# Purpose:
# This file takes a given Batch created by DNA_Generator.py and tells blender to render the image or export a 3D model to
# the NFT_Output folder.

import bpy
import os
import ssl
import time
import json
import smtplib
import datetime
import platform
import re
from .loading_animation import Loader
from .Constants import bcolors, removeList, remove_file_by_extension
from .Metadata import createCardanoMetadata, createSolanaMetaData, createErc721MetaData


# Save info
def save_batch(batch, file_name):
    saved_batch = json.dumps(batch, indent=1, ensure_ascii=True)

    with open(os.path.join(file_name), 'w') as outfile:
        outfile.write(saved_batch + '\n')


def save_generation_state(input):
    """Saves date and time of generation start, and generation types; Images, Animations, 3D Models, and the file types for each."""
    file_name = os.path.join(input.batch_json_save_path, "Batch{}.json".format(input.batchToGenerate))
    batch = json.load(open(file_name))

    CURRENT_TIME = datetime.datetime.now().strftime("%H:%M:%S")
    CURRENT_DATE = datetime.datetime.now().strftime("%d/%m/%Y")
    LOCAL_TIMEZONE = str(datetime.datetime.now(datetime.timezone.utc))

    if "Generation Save" in batch:
        batch_save_number = int(batch[f"Generation Save"].index(batch[f"Generation Save"][-1]))
    else:
        batch_save_number = 0

    batch["Generation Save"] = list()
    batch["Generation Save"].append({
        "Batch Save Number": batch_save_number + 1,
        "DNA Generated": None,
        "Generation Start Date and Time": [CURRENT_TIME, CURRENT_DATE, LOCAL_TIMEZONE],
        "Render_Settings": {
            "nftName": input.nftName,
            "save_path": input.save_path,
            "nftsPerBatch": input.nftsPerBatch,
            "batchToGenerate": input.batchToGenerate,
            "collectionSize": input.collectionSize,

            "Blend_My_NFTs_Output": input.Blend_My_NFTs_Output,
            "batch_json_save_path": input.batch_json_save_path,
            "nftBatch_save_path": input.nftBatch_save_path,

            "enableImages": input.enableImages,
            "imageFileFormat": input.imageFileFormat,

            "enableAnimations": input.enableAnimations,
            "animationFileFormat": input.animationFileFormat,

            "enableModelsBlender": input.enableModelsBlender,
            "modelFileFormat": input.modelFileFormat,

            "enableCustomFields": input.enableCustomFields,

            "cardanoMetaDataBool": input.cardanoMetaDataBool,
            "solanaMetaDataBool": input.solanaMetaDataBool,
            "erc721MetaData": input.erc721MetaData,

            "cardano_description": input.cardano_description,
            "solana_description": input.solana_description,
            "erc721_description": input.erc721_description,

            "enableMaterials": input.enableMaterials,
            "materialsFile": input.materialsFile,

            "enableLogic": input.enableLogic,
            "enable_Logic_Json": input.enable_Logic_Json,
            "logicFile": input.logicFile,

            "enableRarity": input.enableRarity,

            "enableAutoShutdown": input.enableAutoShutdown,

            "specify_timeBool": input.specify_timeBool,
            "hours": input.hours,
            "minutes": input.minutes,

            "emailNotificationBool": input.emailNotificationBool,
            "sender_from": input.sender_from,
            "email_password": input.email_password,
            "receiver_to": input.receiver_to,

            "custom_Fields": input.custom_Fields,
        },
    })

    save_batch(batch, file_name)


def save_completed(full_single_dna, a, x, batch_json_save_path, batchToGenerate):
    """Saves progress of rendering to batch.json file."""

    file_name = os.path.join(batch_json_save_path, "Batch{}.json".format(batchToGenerate))
    batch = json.load(open(file_name))
    index = batch["BatchDNAList"].index(a)
    batch["BatchDNAList"][index][full_single_dna]["Complete"] = True
    batch["Generation Save"][-1]["DNA Generated"] = x

    save_batch(batch, file_name)


# Exporter functions:
def getBatchData(batchToGenerate, batch_json_save_path):
    """
    Retrieves a given batches data determined by renderBatch in config.py
    """

    file_name = os.path.join(batch_json_save_path, "Batch{}.json".format(batchToGenerate))
    batch = json.load(open(file_name))

    NFTs_in_Batch = batch["NFTs_in_Batch"]
    hierarchy = batch["hierarchy"]
    BatchDNAList = batch["BatchDNAList"]

    return NFTs_in_Batch, hierarchy, BatchDNAList


def render_and_save_NFTs(input):
    """
    Renders the NFT DNA in a Batch#.json, where # is renderBatch in config.py. Turns off the viewport camera and
    the render camera for all items in hierarchy.
    """

    time_start_1 = time.time()

    # If failed Batch is detected and user is resuming its generation:
    if input.fail_state:
        print(f"{bcolors.ERROR}\nResuming Failed Batch {input.failed_batch}\n{bcolors.RESET}")
        NFTs_in_Batch, hierarchy, BatchDNAList = getBatchData(input.failed_batch, input.batch_json_save_path)
        for a in range(input.failed_dna):
            del BatchDNAList[0]
        x = input.failed_dna + 1

    # If user is generating the normal way:
    else:
        print(f"\nGenerating Batch {input.batchToGenerate}\n")
        NFTs_in_Batch, hierarchy, BatchDNAList = getBatchData(input.batchToGenerate, input.batch_json_save_path)
        save_generation_state(input)
        x = 1

    if input.enableMaterials:
        materialsFile = json.load(open(input.materialsFile))

    for a in BatchDNAList:
        full_single_dna = list(a.keys())[0]
        Order_Num = a[full_single_dna]['Order_Num']

        # Material handling:
        if input.enableMaterials:
            single_dna, material_dna = full_single_dna.split(':')

        if not input.enableMaterials:
            single_dna = full_single_dna

        def getListMaterialDNADeconstructed(material_dna):
            """
            Returns a list of materials, which are also a list ( because now, there can be more than one material for Variant Object).
            example: 
            - input material_dna: "(1)-(2)-(1-4)-(3-13)"
            - output: ['1', '2', '1-4', '3-13']
            Important: module 're' necessary
            """
            result = re.findall(r'\(.*?\)', material_dna)
            result = [i[1:-1] for i in result]
            return result
        
        def match_DNA_to_Variant(single_dna):
            """
            Matches each DNA number separated by "-" to its attribute, then its variant.
            """

            listAttributes = list(hierarchy.keys())
            listDnaDecunstructed = single_dna.split('-')
            dnaDictionary = {}

            for i, j in zip(listAttributes, listDnaDecunstructed):
                dnaDictionary[i] = j

            for x in dnaDictionary:
                for k in hierarchy[x]:
                    kNum = hierarchy[x][k]["number"]
                    if kNum == dnaDictionary[x]:
                        dnaDictionary.update({x: k})
            return dnaDictionary

        def match_materialDNA_to_Material(single_dna, material_dna, materialsFile):
            """
            Matches the Material DNA to it's selected Materials unless a 0 is present meaning no material for that variant was selected.
            Changes made:
            Now Material DNA can look like this: (11-21)-(31).
            """
            listAttributes = list(hierarchy.keys())
            listDnaDecunstructed = single_dna.split('-')
            listMaterialDNADeconstructed = getListMaterialDNADeconstructed(material_dna)

            full_dna_dict = {}

            for attribute, variant, material in zip(listAttributes, listDnaDecunstructed, listMaterialDNADeconstructed):
                materials_list_to_dict = []

                for var in hierarchy[attribute]:
                    if hierarchy[attribute][var]['number'] == variant:
                        variant = var

                if material != '0':  # If material is not empty
                    for sub_mat_idx, sub_material in enumerate(material.split('-')):
                        for variant_m in materialsFile:
                            if variant == variant_m:
                                for mat_dict_idx, mat_dict in enumerate(materialsFile[variant_m]["Material List"]):
                                    if sub_mat_idx == mat_dict_idx:
                                        # Getting Materials name from Materials index in the Materials List
                                        materials_list = list(mat_dict.keys())
                                        material = materials_list[int(sub_material) - 1]  # Subtract 1 because '0' means empty mat
                                        materials_list_to_dict.append(material)
                                        # TODO: if sub_material == 0 then int(sub_material) - 1 = -1 => no error, but last element of array
                                        
                else:
                    materials_list_to_dict.append(material)
                
                full_dna_dict[variant] = materials_list_to_dict

            return full_dna_dict
        
        def get_frame_end(single_dna, animation_order_num_dna=2):
            """
            Find frame_end for frame range in order to render number of frames corresponding to number of frames of chosen animation
            """
            animations = hierarchy["Animations"]
            animation_num_from_dna = single_dna.split('-')[animation_order_num_dna-1]
            
            for animation in animations:
                if animations[animation]['number'] == animation_num_from_dna:
                    frame_end = int(animation.split('-')[1].split('_')[0])
                    break

            return frame_end


        metadataMaterialDict = {}

        if input.enableMaterials:
            materialdnaDictionary = match_materialDNA_to_Material(single_dna, material_dna, materialsFile)

            for var_mat in list(materialdnaDictionary.keys()):
                if materialdnaDictionary[var_mat] != ['0']:
                    if not materialsFile[var_mat]['Variant Objects']:
                        """
                        If objects to apply material to not specified, apply to all objects in Variant collection.
                        """
                        metadataMaterialDict[var_mat] = materialdnaDictionary[var_mat]

                        for obj in bpy.data.collections[var_mat].all_objects:
                            selected_object = bpy.data.objects.get(obj.name)
                            selected_object.active_material = bpy.data.materials[materialdnaDictionary[var_mat]]

                    if materialsFile[var_mat]['Variant Objects']:
                        """
                        If objects to apply material to are specified, apply material only to objects specified withing the Variant collection.
                        """
                        metadataMaterialDict[var_mat] = materialdnaDictionary[var_mat]

                        for index, obj_list in enumerate(materialsFile[var_mat]['Variant Objects']):
                            for  obj in obj_list:
                                selected_object = bpy.data.objects.get(obj)
                                selected_object.active_material = bpy.data.materials[materialdnaDictionary[var_mat][index]]

        # Turn off render camera and viewport camera for all collections in hierarchy
        for i in hierarchy:
            for j in hierarchy[i]:
                try:
                    bpy.data.collections[j].hide_render = True
                    bpy.data.collections[j].hide_viewport = True
                except KeyError:
                    raise TypeError(
                        f"\n{bcolors.ERROR}Blend_My_NFTs Error:\n"
                        f"The Collection '{j}' appears to be missing or has been renamed. If you made any changes to "
                        f"your .blned file scene, ensure you re-create your NFT Data so Blend_My_NFTs can read your scene."
                        f"For more information see:{bcolors.RESET}"
                        f"\nhttps://github.com/torrinworx/Blend_My_NFTs#blender-file-organization-and-structure\n"
                    )

        dnaDictionary = match_DNA_to_Variant(single_dna)
        name = input.nftName + "_" + str(Order_Num)

        # Change Text Object in Scene to match DNA string:
        # Variables that can be used: full_single_dna, name, Order_Num
        # ob = bpy.data.objects['Text']  # Object name
        # ob.data.body = str(f"DNA: {full_single_dna}")  # Set text of Text Object ob

        print(f"\n{bcolors.OK}|--- Generating NFT {x}/{NFTs_in_Batch}: {name} ---|{bcolors.RESET}")
        print(f"DNA attribute list:\n{dnaDictionary}\nDNA Code:{single_dna}")

        for c in dnaDictionary:
            collection = dnaDictionary[c]
            if collection != '0':
                bpy.data.collections[collection].hide_render = False
                bpy.data.collections[collection].hide_viewport = False

        time_start_2 = time.time()

        # Main paths for batch subfolders:
        batchFolder = os.path.join(input.nftBatch_save_path, "Batch" + str(input.batchToGenerate))

        imageFolder = os.path.join(batchFolder, "Images")
        animationFolder = os.path.join(batchFolder, "Animations")
        modelFolder = os.path.join(batchFolder, "Models")
        BMNFT_metaData_Folder = os.path.join(batchFolder, "BMNFT_metadata")

        imagePath = os.path.join(imageFolder, name)
        animationPath = os.path.join(animationFolder, name)
        modelPath = os.path.join(modelFolder, name)

        cardanoMetadataPath = os.path.join(batchFolder, "Cardano_metadata")
        solanaMetadataPath = os.path.join(batchFolder, "Solana_metadata")
        erc721MetadataPath = os.path.join(batchFolder, "Erc721_metadata")


        def check_failed_exists(file_path):
            # Delete a file if a fail state is detected and if the file being re-generated already exists. Prevents
            # animations from corrupting.

            if input.fail_state:
                if os.path.exists(file_path):
                    os.remove(file_path)

        # Generation/Rendering:
        if input.enableImages:

            print(f"{bcolors.OK}---Image---{bcolors.RESET}")

            image_render_time_start = time.time()

            check_failed_exists(imagePath)

            def render_image():
                if not os.path.exists(imageFolder):
                    os.makedirs(imageFolder)

                bpy.context.scene.render.filepath = imagePath
                bpy.context.scene.render.image_settings.file_format = input.imageFileFormat
                bpy.ops.render.render(write_still=True)

            # Loading Animation:
            loading = Loader(f'Rendering Image {x}/{NFTs_in_Batch}...', '').start()
            render_image()
            loading.stop()

            image_render_time_end = time.time()

            print(
                f"{bcolors.OK}Rendered image in {image_render_time_end - image_render_time_start}s.\n{bcolors.RESET}"
            )

        if input.enableAnimations:
            print(f"{bcolors.OK}---Animation---{bcolors.RESET}")

            animation_render_time_start = time.time()

            check_failed_exists(animationPath)

            def render_animation():
                if not os.path.exists(animationFolder):
                    os.makedirs(animationFolder)

                if input.animationFileFormat == "MP4":
                    bpy.context.scene.render.filepath = animationPath
                    bpy.context.scene.render.image_settings.file_format = "FFMPEG"

                    bpy.context.scene.render.ffmpeg.format = 'MPEG4'
                    bpy.context.scene.render.ffmpeg.codec = 'H264'
                    bpy.ops.render.render(animation=True)

                elif input.animationFileFormat == 'PNG':
                    if not os.path.exists(animationPath):
                        os.makedirs(animationPath)

                    bpy.context.scene.frame_start = 1
                    bpy.context.scene.frame_end = get_frame_end(single_dna, 1) # set frame end to number corresponding with animation lenght
                    bpy.context.scene.render.filepath = os.path.join(animationPath, name)
                    bpy.context.scene.render.image_settings.file_format = input.animationFileFormat
                    bpy.ops.render.render(animation=True)
                    

                elif input.animationFileFormat == 'TIFF':
                    if not os.path.exists(animationPath):
                        os.makedirs(animationPath)

                    bpy.context.scene.render.filepath = os.path.join(animationPath, name)
                    bpy.context.scene.render.image_settings.file_format = input.animationFileFormat
                    bpy.ops.render.render(animation=True)

                else:
                    bpy.context.scene.render.filepath = animationPath
                    bpy.context.scene.render.image_settings.file_format = input.animationFileFormat
                    bpy.ops.render.render(animation=True)

            # Loading Animation:
            loading = Loader(f'Rendering Animation {x}/{NFTs_in_Batch}...', '').start()
            render_animation()
            loading.stop()

            animation_render_time_end = time.time()

            print(
                f"{bcolors.OK}Rendered animation in {animation_render_time_end - animation_render_time_start}s.\n{bcolors.RESET}"
            )

        if input.enableModelsBlender:
            print(f"{bcolors.OK}---3D Model---{bcolors.RESET}")

            model_generation_time_start = time.time()

            def generate_models():
                if not os.path.exists(modelFolder):
                    os.makedirs(modelFolder)

                for i in dnaDictionary:
                    coll = dnaDictionary[i]
                    if coll != '0':
                        for obj in bpy.data.collections[coll].all_objects:
                            obj.select_set(True)

                for obj in bpy.data.collections['Script_Ignore'].all_objects:
                    obj.select_set(True)

                # Remove objects from 3D model export:
                # remove_objects: list = [
                # ]
                #
                # for obj in bpy.data.objects:
                #     if obj.name in remove_objects:
                #         obj.select_set(False)

                if input.modelFileFormat == 'GLB':
                    check_failed_exists(f"{modelPath}.glb")
                    bpy.ops.export_scene.gltf(filepath=f"{modelPath}.glb",
                                              check_existing=True,
                                              export_format='GLB',
                                              export_keep_originals=True,
                                              use_selection=True)
                if input.modelFileFormat == 'GLTF_SEPARATE':
                    check_failed_exists(f"{modelPath}.gltf")
                    check_failed_exists(f"{modelPath}.bin")
                    bpy.ops.export_scene.gltf(filepath=f"{modelPath}",
                                              check_existing=True,
                                              export_format='GLTF_SEPARATE',
                                              export_keep_originals=True,
                                              use_selection=True)
                if input.modelFileFormat == 'GLTF_EMBEDDED':
                    check_failed_exists(f"{modelPath}.gltf")
                    bpy.ops.export_scene.gltf(filepath=f"{modelPath}.gltf",
                                              check_existing=True,
                                              export_format='GLTF_EMBEDDED',
                                              export_keep_originals=True,
                                              use_selection=True)
                elif input.modelFileFormat == 'FBX':
                    check_failed_exists(f"{modelPath}.fbx")
                    bpy.ops.export_scene.fbx(filepath=f"{modelPath}.fbx",
                                             check_existing=True,
                                             use_selection=True)
                elif input.modelFileFormat == 'OBJ':
                    check_failed_exists(f"{modelPath}.obj")
                    bpy.ops.export_scene.obj(filepath=f"{modelPath}.obj",
                                             check_existing=True,
                                             use_selection=True, )
                elif input.modelFileFormat == 'X3D':
                    check_failed_exists(f"{modelPath}.x3d")
                    bpy.ops.export_scene.x3d(filepath=f"{modelPath}.x3d",
                                             check_existing=True,
                                             use_selection=True)
                elif input.modelFileFormat == 'STL':
                    check_failed_exists(f"{modelPath}.stl")
                    bpy.ops.export_mesh.stl(filepath=f"{modelPath}.stl",
                                            check_existing=True,
                                            use_selection=True)
                elif input.modelFileFormat == 'VOX':
                    check_failed_exists(f"{modelPath}.vox")
                    bpy.ops.export_vox.some_data(filepath=f"{modelPath}.vox")

            # Loading Animation:
            loading = Loader(f'Generating 3D model {x}/{NFTs_in_Batch}...', '').start()
            generate_models()
            loading.stop()

            model_generation_time_end = time.time()

            print(
                f"{bcolors.OK}Generated 3D model in {model_generation_time_end - model_generation_time_start}s.\n{bcolors.RESET}"
            )

        # Generating Metadata:
        if input.cardanoMetaDataBool:
            if not os.path.exists(cardanoMetadataPath):
                os.makedirs(cardanoMetadataPath)
            createCardanoMetadata(name, Order_Num, full_single_dna, dnaDictionary, metadataMaterialDict,
                                  input.custom_Fields,
                                  input.enableCustomFields, input.cardano_description, cardanoMetadataPath)

        if input.solanaMetaDataBool:
            if not os.path.exists(solanaMetadataPath):
                os.makedirs(solanaMetadataPath)
            createSolanaMetaData(name, Order_Num, full_single_dna, dnaDictionary, metadataMaterialDict,
                                 input.custom_Fields,
                                 input.enableCustomFields, input.solana_description, solanaMetadataPath)

        if input.erc721MetaData:
            if not os.path.exists(erc721MetadataPath):
                os.makedirs(erc721MetadataPath)
            createErc721MetaData(name, Order_Num, full_single_dna, dnaDictionary, metadataMaterialDict,
                                 input.custom_Fields,
                                 input.enableCustomFields, input.erc721_description, erc721MetadataPath)

        if not os.path.exists(BMNFT_metaData_Folder):
            os.makedirs(BMNFT_metaData_Folder)

        for b in dnaDictionary:
            if dnaDictionary[b] == "0":
                dnaDictionary[b] = "Empty"

        metaDataDict = {"name": name, "NFT_DNA": a, "NFT_Variants": dnaDictionary,
                        "Material_Attributes": metadataMaterialDict}

        jsonMetaData = json.dumps(metaDataDict, indent=1, ensure_ascii=True)

        with open(os.path.join(BMNFT_metaData_Folder, "Data_" + name + ".json"), 'w') as outfile:
            outfile.write(jsonMetaData + '\n')

        print(f"Completed {name} render in {time.time() - time_start_2}s")

        save_completed(full_single_dna, a, x, input.batch_json_save_path, input.batchToGenerate)

        x += 1

    for i in hierarchy:
        for j in hierarchy[i]:
            bpy.data.collections[j].hide_render = False
            bpy.data.collections[j].hide_viewport = False

    batch_complete_time = time.time() - time_start_1

    print(f"\nAll NFTs successfully generated and sent to {input.nftBatch_save_path}"
          f"\nCompleted all renders in Batch{input.batchToGenerate}.json in {batch_complete_time}s\n")

    batch_info = {"Batch Render Time": batch_complete_time, "Number of NFTs generated in Batch": x - 1,
                  "Average time per generation": batch_complete_time / x - 1}

    batch_infoFolder = os.path.join(input.nftBatch_save_path, "Batch" + str(input.batchToGenerate), "batch_info.json")
    save_batch(batch_info, batch_infoFolder)

    # Send Email that Batch is complete:
    if input.emailNotificationBool:
        port = 465  # For SSL
        smtp_server = "smtp.gmail.com"
        sender_email = input.sender_from  # Enter your address
        receiver_email = input.receiver_to  # Enter receiver address
        password = input.email_password

        # Get batch info for message:
        if input.fail_state:
            batch = input.fail_state
            batchData = getBatchData(input.failed_batch, input.batch_json_save_path)

        else:
            batchData = getBatchData(input.batchToGenerate, input.batch_json_save_path)

            batch = input.batchToGenerate

        generation_time = str(datetime.timedelta(seconds=batch_complete_time))

        message = f"""\
        Subject: Batch {batch} completed {x - 1} NFTs in {generation_time} (h:m:s)

        Generation Time:
        {generation_time.split(':')[0]} Hours, {generation_time.split(':')[1]} Minutes, {generation_time.split(':')[2]} Seconds
        Batch Data:

            {batchData}

        This message was sent from an instance of the Blend_My_NFTs Blender add-on.
        """

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message)

    # Automatic Shutdown:
    # If user selects automatic shutdown but did not specify time after Batch completion
    def shutdown(time):
        plateform = platform.system()

        if plateform == "Windows":
            os.system(f"shutdown /s /t {time}")
        if plateform == "Darwin":
            os.system(f"shutdown /s /t {time}")

    if input.enableAutoShutdown and not input.specify_timeBool:
        shutdown(0)

    # If user selects automatic shutdown and specify time after Batch completion
    if input.enableAutoShutdown and input.specify_timeBool:
        hours = (int(input.hours) / 60) / 60
        minutes = int(input.minutes) / 60
        total_sleep_time = hours + minutes

        # time.sleep(total_sleep_time)

        shutdown(total_sleep_time)
