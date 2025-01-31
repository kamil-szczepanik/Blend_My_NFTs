# Purpose:
# This file generates NFT DNA based on a .blend file scene structure and exports NFTRecord.json.

from traceback import print_tb
import bpy
import os
import re
import copy
import time
import json
import random
from functools import partial
from .loading_animation import Loader
from . import Rarity, Logic, Checks, Material_Generator
from .Constants import bcolors, removeList, remove_file_by_extension


def get_hierarchy():
    """
    Returns the hierarchy of a given Blender scene.
    """

    coll = bpy.context.scene.collection

    scriptIgnoreCollection = bpy.data.collections["Script_Ignore"]

    listAllCollInScene = []
    listAllCollections = []

    def traverse_tree(t):
        yield t
        for child in t.children:
            yield from traverse_tree(child)

    for c in traverse_tree(coll):
        listAllCollInScene.append(c)

    for i in listAllCollInScene:
        listAllCollections.append(i.name)

    listAllCollections.remove(scriptIgnoreCollection.name)

    if "Scene Collection" in listAllCollections:
        listAllCollections.remove("Scene Collection")

    if "Master Collection" in listAllCollections:
        listAllCollections.remove("Master Collection")

    def allScriptIgnore(scriptIgnoreCollection):
        # Removes all collections, sub collections in Script_Ignore collection from listAllCollections.

        for coll in list(scriptIgnoreCollection.children):
            listAllCollections.remove(coll.name)
            listColl = list(coll.children)
            if len(listColl) > 0:
                allScriptIgnore(coll)

    allScriptIgnore(scriptIgnoreCollection)
    listAllCollections.sort()

    exclude = ["_"]  # Excluding characters that identify a Variant
    attributeCollections = copy.deepcopy(listAllCollections)

    def filter_num():
        """
        This function removes items from 'attributeCollections' if they include values from the 'exclude' variable.
        It removes child collections from the parent collections in from the "listAllCollections" list.
        """
        for x in attributeCollections:
            if any(a in x for a in exclude):
                attributeCollections.remove(x)

    for i in range(len(listAllCollections)):
        filter_num()

    attributeVariants = [x for x in listAllCollections if x not in attributeCollections]
    attributeCollections1 = copy.deepcopy(attributeCollections)

    def attributeData(attributeVariants):
        """
      Creates a dictionary of each attribute
      """
        allAttDataList = {}
        for i in attributeVariants:
            # Check if name follows naming conventions:
            if int(i.count("_")) > 2 and int(i.split("_")[1]) > 0:
                raise Exception(
                    f"\n{bcolors.ERROR}Blend_My_NFTs Error:\n"
                    f"There is a naming issue with the following Attribute/Variant: '{i}'\n"
                    f"Review the naming convention of Attribute and Variant collections here:\n{bcolors.RESET}"
                    f"https://github.com/torrinworx/Blend_My_NFTs#blender-file-organization-and-structure\n"
                )

            try:
                number = i.split("_")[1]
                name = i.split("_")[0]
                rarity = i.split("_")[2]
            except IndexError:
                raise Exception(
                    f"\n{bcolors.ERROR}Blend_My_NFTs Error:\n"
                    f"There is a naming issue with the following Attribute/Variant: '{i}'\n"
                    f"Review the naming convention of Attribute and Variant collections here:\n{bcolors.RESET}"
                    f"https://github.com/torrinworx/Blend_My_NFTs#blender-file-organization-and-structure\n"
                )

            allAttDataList[i] = {"name": name, "number": number, "rarity": rarity}
        return allAttDataList

    variantMetaData = attributeData(attributeVariants)

    hierarchy = {}
    for i in attributeCollections1:
        colParLong = list(bpy.data.collections[str(i)].children)
        colParShort = {}
        for x in colParLong:
            colParShort[x.name] = None
        hierarchy[i] = colParShort

    for a in hierarchy:
        for b in hierarchy[a]:
            for x in variantMetaData:
                if str(x) == str(b):
                    (hierarchy[a])[b] = variantMetaData[x]

    return hierarchy


def generateNFT_DNA(collectionSize, enableRarity, rarityFile, enableLogic, logicFile, enableMaterials, materialsFile):
    """
   Returns batchDataDictionary containing the number of NFT combinations, hierarchy, and the DNAList.
   """
    counter = 0

    jack_o_lantern_num = 1*collectionSize/100
    jack_o_lantern_counter = 0

    hierarchy = get_hierarchy()

    # DNA random, Rarity and Logic methods:
    DataDictionary = {}

    def synchronize_logic_to_hierarchy(logic, hierarchy):
        """
        Now rairty from logic file is not important, 
        although there has to be some placeholder in its place e.g. Color_2_X
        It also checks if Variants in Logic file are named correctly
        """

        wrong_variants = []
        for rule_num, rule in logic.items():
            for key, logic_variant_group in rule.items():
                for logic_variant_index, logic_variant in enumerate(logic_variant_group):
                    if len(logic_variant.split('_')) != 3:
                        wrong_variants.append(logic_variant)

                    logic_name_and_num = '_'.join(logic_variant.split('_')[:2])
                    logic_variant_found_in_hierarchy = False

                    for attribute in hierarchy:
                        for hierarchy_variant in hierarchy[attribute]:
                            if logic_name_and_num in hierarchy_variant:
                                variant_rarity = hierarchy_variant.split('_')[-1]
                                logic[rule_num][key][logic_variant_index] = f"{logic_name_and_num}_{variant_rarity}"
                                logic_variant_found_in_hierarchy = True

                    if logic_variant_found_in_hierarchy == False:
                        wrong_variants.append(logic_variant)

        wrong_variants = set(wrong_variants)
        if len(wrong_variants) != 0:
            raise Exception(f"There are incorrectly named variant in Logic file! Those variants are:{wrong_variants}")
        else:
            return logic
    
    def synchronize_materials_to_hierarchy(materials, hierarchy):
        """
        Now rairty from logic file is not important, 
        although there has to be some placeholder in its place e.g. Color_2_X
        It also checks if Variants in Material file are named correctly
        """
        new_materials = {}
        wrong_variants = []

        for materials_variant in materials:
            if len(materials_variant.split('_')) != 3:
                wrong_variants.append(materials_variant)
            materials_name_and_num = '_'.join(materials_variant.split('_')[:2])
            materials_variant_found_in_hierarchy = False

            for attribute in hierarchy:
                for hierarchy_variant in hierarchy[attribute]:
                    if materials_name_and_num in hierarchy_variant:

                        variant_rarity = hierarchy_variant.split('_')[-1]
                        new_materials[f"{materials_name_and_num}_{variant_rarity}"] = materials[materials_variant]
                        materials_variant_found_in_hierarchy = True

            if materials_variant_found_in_hierarchy == False:
                wrong_variants.append(materials_variant)
                
        wrong_variants = set(wrong_variants)
        if len(wrong_variants) != 0:
            raise Exception(f"There are incorrectly named variant in Material file! Those variants are:{wrong_variants}")
        else:
            ledger = json.dumps(new_materials, indent=1, ensure_ascii=True)
            with open(materialsFilePath, 'w') as outfile:
                outfile.write(ledger + '\n')

            return new_materials

    def check_variant_objects_in_material_file(materialFile):
        wrong_mat_variant_objects = []

        scene_obj_list = list(bpy.data.objects.keys())

        for variant in materialFile:
            for variant_object_list in materialFile[variant]["Variant Objects"]:
                for variant_object in variant_object_list:
                    
                    variant_object_found = False
                    for obj in scene_obj_list:
                        if obj == variant_object:
                            variant_object_found = True
                            break
                    
                    if variant_object_found == False:
                        wrong_mat_variant_objects.append(variant_object)
        
        if len(wrong_mat_variant_objects) != 0:
            raise Exception(f"There are incorrectly named variant objects in Material file! Those objects are:{wrong_mat_variant_objects}")
        else:
            return True

    def check_materials_in_material_file(materialFile):
        wrong_materials = []
        bpy_materials = bpy.data.materials.keys()

        for variant in materialFile:
            for materials_dict in materialFile[variant]["Material List"]:
                for material in materials_dict:
                    
                    material_found = False
                    for mat in bpy_materials:
                        if mat == material:
                            material_found = True
                            break
                    
                    if material_found == False:
                        wrong_materials.append(material)
        
        if len(wrong_materials) != 0:
            raise Exception(f"There are incorrectly named materials in Material file! Those objects are:{wrong_materials}")
        else:
            return True

    def check_RarityFile(hierarchy, rarity):
        for attribute in hierarchy:
            for variant in hierarchy[attribute]:
                variant_found_flag = False
                
                for att_rarity in rarity:
                    for var_rarity in rarity[att_rarity]:
                        if var_rarity==variant:
                            variant_found_flag=True
                if variant_found_flag==False:
                    raise Exception(f"Variant from hierarchy in blender not found in RarityFile.json. Variant name: {variant}")

        return True

    def update_hierarchy_with_values_from_RarityFile(hierarchy, rarity):
        for attribute in hierarchy:
            for variant in hierarchy[attribute]:
                hierarchy[attribute][variant]["rarity"] = rarity[attribute][variant]

        return hierarchy

    def check_if_variant_in_DNA(singleDNA, dna_order_num, variant_num):
        """
        dna_order_num and variant_num counting from 1
        """
        deconstructed_DNA = singleDNA.split("-")
        hat_variant = deconstructed_DNA[dna_order_num-1]
        if hat_variant==str(variant_num):
            return True
        else:
            return False

    
    if enableLogic:
        logicFile = synchronize_logic_to_hierarchy(logicFile, hierarchy)
    
    if enableMaterials:
        materialsFilePath = materialsFile
        materialsFile = json.load(open(materialsFilePath))
        materialsFile = synchronize_materials_to_hierarchy(materialsFile, hierarchy)
        check_variant_objects_in_material_file(materialsFile)
        check_materials_in_material_file(materialsFile)

    if enableRarity:
        rarity = json.load(open(rarityFile))
        check_RarityFile(hierarchy, rarity)
        hierarchy = update_hierarchy_with_values_from_RarityFile(hierarchy, rarity)


    def createDNArandom(hierarchy):
        """Creates a single DNA randomly without Rarity or Logic."""
        dnaStr = ""
        dnaStrList = []
        listOptionVariant = []

        for i in hierarchy:
            numChild = len(hierarchy[i])
            possibleNums = list(range(1, numChild + 1))
            listOptionVariant.append(possibleNums)

        for i in listOptionVariant:
            randomVariantNum = random.choices(i, k=1)
            str1 = ''.join(str(e) for e in randomVariantNum)
            dnaStrList.append(str1)

        for i in dnaStrList:
            num = "-" + str(i)
            dnaStr += num

        dna = ''.join(dnaStr.split('-', 1))

        return str(dna)

    def singleCompleteDNA():
        """
        This function applies Rarity and Logic to a single DNA created by createDNASingle() if Rarity or Logic specified
        """

        singleDNA = ""
        # Comments for debugging random, rarity, logic, and materials.
        if not enableRarity:
            singleDNA = createDNArandom(hierarchy)
        # print("============")
        # print(f"Original DNA: {singleDNA}")
        if enableRarity:
            singleDNA = Rarity.createDNArarity(hierarchy)
        # print(f"Rarity DNA: {singleDNA}")

        if enableLogic:
            singleDNA = Logic.logicafyDNAsingle(hierarchy, singleDNA, logicFile, enableRarity, enableMaterials)

            nonlocal jack_o_lantern_counter
            nonlocal jack_o_lantern_num
            while check_if_variant_in_DNA(singleDNA, 16, 23) and jack_o_lantern_counter >= jack_o_lantern_num:
                singleDNA = Rarity.createDNArarity(hierarchy)
                singleDNA = Logic.logicafyDNAsingle(hierarchy, singleDNA, logicFile, enableRarity, enableMaterials)
            if check_if_variant_in_DNA(singleDNA, 16, 23) and jack_o_lantern_counter < jack_o_lantern_num:
                jack_o_lantern_counter+=1


        # print(f"Logic DNA: {singleDNA}")

        if enableMaterials:
            singleDNA = Material_Generator.apply_materials(hierarchy, singleDNA, materialsFile, enableRarity)
        # print(f"Materials DNA: {singleDNA}")

        # print("============\n")

        nonlocal counter
        counter += 1
        print(counter)

        return singleDNA

    def create_DNAList():
        """Creates DNAList. Loops through createDNARandom() and applies Rarity, and Logic while checking if all DNA are unique"""
        DNASetReturn = set()

        for i in range(collectionSize):
            dnaPushToList = partial(singleCompleteDNA)

            DNASetReturn |= {''.join([dnaPushToList()]) for _ in range(collectionSize - len(DNASetReturn))}

        DNAListUnformatted = list(DNASetReturn)

        DNAListFormatted = []
        DNA_Counter = 1
        for i in DNAListUnformatted:
            DNAListFormatted.append({
                i: {
                    "Complete": False,
                    "Order_Num": DNA_Counter
                }
            })

            DNA_Counter += 1

        return DNAListFormatted
    
    def create_attributes_hierarchy_dict(hierarchy):
        attributes_hierarchy = {}
        for index, attribute in enumerate(hierarchy):
            attributes_hierarchy[index+1] = attribute
        return attributes_hierarchy

    DNAList = create_DNAList()

    # Messages:

    Checks.raise_Warning_collectionSize(DNAList, collectionSize)

    # Data stored in batchDataDictionary:
    DataDictionary["numNFTsGenerated"] = len(DNAList)
    DataDictionary["attributes_hierarchy"] = create_attributes_hierarchy_dict(hierarchy)
    DataDictionary["hierarchy"] = hierarchy
    DataDictionary["DNAList"] = DNAList

    return DataDictionary


def makeBatches(collectionSize, nftsPerBatch, save_path, batch_json_save_path):
    """
   Sorts through all the batches and outputs a given number of batches depending on collectionSize and nftsPerBatch.
   These files are then saved as Batch#.json files to batch_json_save_path
   """

    # Clears the Batch Data folder of Batches:
    batchList = os.listdir(batch_json_save_path)
    if batchList:
        for i in batchList:
            batch = os.path.join(batch_json_save_path, i)
            if os.path.exists(batch):
                os.remove(
                    os.path.join(batch_json_save_path, i)
                )

    Blend_My_NFTs_Output = os.path.join(save_path, "Blend_My_NFTs Output", "NFT_Data")
    NFTRecord_save_path = os.path.join(Blend_My_NFTs_Output, "NFTRecord.json")
    DataDictionary = json.load(open(NFTRecord_save_path))

    numNFTsGenerated = DataDictionary["numNFTsGenerated"]
    hierarchy = DataDictionary["hierarchy"]
    DNAList = DataDictionary["DNAList"]

    numBatches = collectionSize // nftsPerBatch
    remainder_dna = collectionSize % nftsPerBatch
    if remainder_dna > 0:
        numBatches += 1

    print(f"To generate batches of {nftsPerBatch} DNA sequences per batch, with a total of {numNFTsGenerated}"
          f" possible NFT DNA sequences, the number of batches generated will be {numBatches}")

    batches_dna_list = []

    for i in range(numBatches):
        BatchDNAList = []
        if i != range(numBatches)[-1]:
            BatchDNAList = list(DNAList[0:nftsPerBatch])
            batches_dna_list.append(BatchDNAList)

            DNAList = [x for x in DNAList if x not in BatchDNAList]
        else:
            BatchDNAList = DNAList

        batchDictionary = {
            "NFTs_in_Batch": int(len(BatchDNAList)),
            "hierarchy": hierarchy,
            "BatchDNAList": BatchDNAList
        }

        batchDictionary = json.dumps(batchDictionary, indent=1, ensure_ascii=True)

        with open(os.path.join(batch_json_save_path, f"Batch{i + 1}.json"), "w") as outfile:
            outfile.write(batchDictionary)


def send_To_Record_JSON(collectionSize, nftsPerBatch, save_path, enableRarity, rarityFile, enableLogic, logicFile, enableMaterials,
                        materialsFile, Blend_My_NFTs_Output, batch_json_save_path):
    """
   Creates NFTRecord.json file and sends "batchDataDictionary" to it. NFTRecord.json is a permanent record of all DNA
   you've generated with all attribute variants. If you add new variants or attributes to your .blend file, other scripts
   need to reference this .json file to generate new DNA and make note of the new attributes and variants to prevent
   repeate DNA.
   """

    # Checking Scene is compatible with BMNFTs:
    Checks.check_Scene()

    # Messages:
    print(
        f"\n========================================\n"
        f"Creating NFT Data. Generating {collectionSize} NFT DNA.\n"
    )

    if not enableRarity and not enableLogic:
        print(
            f"{bcolors.OK}NFT DNA will be determined randomly, no special properties or parameters are applied.\n{bcolors.RESET}")

    if enableRarity:
        print(f"{bcolors.OK}Rarity is ON. Weights listed in .blend scene will be taken into account.\n{bcolors.RESET}")

    if enableLogic:
        print(f"{bcolors.OK}Logic is ON. {len(list(logicFile.keys()))} rules detected and applied.\n{bcolors.RESET}")

    time_start = time.time()

    def create_nft_data():
        try:
            DataDictionary = generateNFT_DNA(collectionSize, enableRarity, rarityFile, enableLogic, logicFile, enableMaterials,
                                             materialsFile)
            numBatches = collectionSize // nftsPerBatch                        
            remainder_dna = collectionSize % nftsPerBatch
            if remainder_dna > 0:
                numBatches += 1                    
            DataDictionary["Number of batches"] = numBatches
            NFTRecord_save_path = os.path.join(Blend_My_NFTs_Output, "NFTRecord.json")

            # Checks:

            Checks.raise_Warning_maxNFTs(nftsPerBatch, collectionSize)
            Checks.check_Duplicates(DataDictionary["DNAList"])
            Checks.raise_Error_ZeroCombinations()

            if enableRarity:
                Checks.check_Rarity(DataDictionary["hierarchy"], DataDictionary["DNAList"],
                                    os.path.join(save_path, "Blend_My_NFTs Output/NFT_Data"))

        except FileNotFoundError:
            raise FileNotFoundError(
                f"\n{bcolors.ERROR}Blend_My_NFTs Error:\n"
                f"Data not saved to NFTRecord.json. Please review your Blender scene and ensure it follows "
                f"the naming conventions and scene structure. For more information, "
                f"see:\n{bcolors.RESET}"
                f"https://github.com/torrinworx/Blend_My_NFTs#blender-file-organization-and-structure\n"
            )
        finally:
            # loading.stop()
            pass

        try:
            ledger = json.dumps(DataDictionary, indent=1, ensure_ascii=True)
            with open(NFTRecord_save_path, 'w') as outfile:
                outfile.write(ledger + '\n')

            print(
                f"\n{bcolors.OK}Blend_My_NFTs Success:\n"
                f"{len(DataDictionary['DNAList'])} NFT DNA saved to {NFTRecord_save_path}. NFT DNA Successfully created.\n{bcolors.RESET}")

        except:
            raise (
                f"\n{bcolors.ERROR}Blend_My_NFTs Error:\n"
                f"Data not saved to NFTRecord.json. Please review your Blender scene and ensure it follows "
                f"the naming conventions and scene structure. For more information, "
                f"see:\n{bcolors.RESET}"
                f"https://github.com/torrinworx/Blend_My_NFTs#blender-file-organization-and-structure\n"
            )

    # Loading Animation:
    # loading = Loader(f'Creating NFT DNA...', '').start()
    create_nft_data()
    makeBatches(collectionSize, nftsPerBatch, save_path, batch_json_save_path)
    # loading.stop()

    time_end = time.time()

    print(
        f"{bcolors.OK}Created and saved NFT DNA in {time_end - time_start}s.\n{bcolors.RESET}"
    )
