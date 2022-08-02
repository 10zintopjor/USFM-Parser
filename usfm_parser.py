from pathlib import Path
from openpecha.core.ids import get_base_id,get_initial_pecha_id,get_alignment_id
from datetime import datetime
from openpecha.core.layer import Layer, LayerEnum
from openpecha.core.pecha import OpenPechaFS 
from openpecha.core.metadata import InitialPechaMetadata,InitialCreationType
from openpecha.core.annotation import AnnBase, Span
from uuid import uuid4
import re




def parse_chapter(page):
    chapters = list(re.finditer(r"\\c \d+",page))

    for index,cur_chapter in enumerate(chapters):
        chapter_verses_map = {}
        chapter_title = cur_chapter.group()
        cur_chapter_start,cur_chapter_end = cur_chapter.span()
        if index < len(chapters)-1:
            next_chapter = chapters[index+1]
            next_chapter_start,next_chapter_end = next_chapter.span()
            cur_chapter_span = (cur_chapter_end,next_chapter_start)
        else:
            cur_chapter_span = (cur_chapter_end,len(page))

        start,end = cur_chapter_span
        cur_text = page[start:end]
        verses_title_cont_map = get_verses(cur_text)
        chapter_verses_map.update({chapter_title:verses_title_cont_map})

    first_chapter_start,_ = chapters[0].span()
    pre_text = remove_usfm_ann(page[:first_chapter_start])
    chapter_verses_map.update({"pre_text":pre_text})
    return chapter_verses_map


def get_verses(text):
    verses_title_cont_map = {}
    verses = list(re.finditer(r"\\v \d+",text))

    for index,cur_verse in enumerate(verses):
        verse_no = cur_verse.group()
        cur_verse_no_start,cur_verse_no_end = cur_verse.span()
        if index < len(verses)-1:
            next_verse = verses[index+1]
            next_verse_no_start,next_verse_no_end = next_verse.span()
            cur_verse_span = (cur_verse_no_end,next_verse_no_start)
        else:
            cur_verse_span = (cur_verse_no_end,len(text))

        start,end = cur_verse_span
        cur_verse_text = text[start:end]
        clean_verse_text = remove_usfm_ann(cur_verse_text)
        verses_title_cont_map.update({verse_no:clean_verse_text})  

    return verses_title_cont_map  

def remove_usfm_ann(ann_text):
    clean_text = re.sub(r"\\+\w+\s?","",ann_text)
    return clean_text.strip()


def create_opf(chapter_verses_map,pecha_id,base_id):
    opf_path = f"opf/{pecha_id}/{pecha_id}.opf"
    opf = OpenPechaFS(path=opf_path)
    base_text = get_base_text(chapter_verses_map)
    bases = {base_id:base_text}
    seg_layer,chapter_verse_ann_id_map = get_segment_layer(chapter_verses_map)
    layers = {base_id:{LayerEnum.segment:seg_layer}}

    opf.base = bases
    opf.layers = layers
    opf.save_base()
    opf.save_layers()

    return chapter_verse_ann_id_map



def get_base_text(chapter_verses_map):
    pre_text = chapter_verses_map["pre_text"]
    base_text = pre_text +"\n\n"
    for chapter in chapter_verses_map:
        if chapter == "pre_text":
            continue
        for verse in chapter_verses_map[chapter]:
            base_text+= chapter_verses_map[chapter][verse]+"\n\n"
    
    return base_text


def get_segment_layer(chapter_verses_map):
    segment_annotations = {}
    chapter_verse_ann_id_map = {}

    char_walker = 0
    pre_text = chapter_verses_map["pre_text"]

    segment_annotation,char_walker = get_segment_annotation(pre_text,char_walker)
    segment_annotations.update(segment_annotation)
    for chapter in chapter_verses_map:
        verse_ann_id_map = {}
        if chapter == "pre_text":
            continue
        for verse in chapter_verses_map[chapter]:
            segment_annotation,char_walker,ann_id = get_segment_annotation(chapter_verses_map[chapter][verse],char_walker)
            segment_annotations.update(segment_annotation)
            verse_ann_id_map.update({verse:ann_id})
    chapter_verse_ann_id_map.update({chapter:verse_ann_id_map})
    segment_layer = Layer(annotation_type=LayerEnum.segment,annotations=segment_annotations)
    
    return segment_layer,chapter_verse_ann_id_map      


def get_segment_annotation(text,char_walker):
    ann_id = uuid4().hex
    segment_annotation = {
           ann_id:AnnBase(span=Span(start=char_walker, end=char_walker + len(text)))
        }

    return (segment_annotation,len(text)+2+char_walker,ann_id)

def parse_usfm_pages(parallel_pages,pecha_ids,alignment_id):
    base_id = get_base_id()
    chapter_verse_ann_id_map_list = []
    for page,pecha_id in zip(parallel_pages,pecha_ids):
        chapter_verses_map = parse_chapter(page)
        chapter_verse_ann_id_map = create_opf(chapter_verses_map,pecha_id,base_id)
        chapter_verse_ann_id_map_list.append(chapter_verse_ann_id_map)
    create_opa(alignment_id,chapter_verse_ann_id_map_list,base_id)


def create_opa(alignmnet_id,chapter_verse_ann_id_map_list,base_id):
    alignment_path = f"./opa/{alignmnet_id}/{alignmnet_id}.opa/{base_id}"
    segment_pairs = get_segment_pairs(chapter_verse_ann_id_map_list)



def get_segment_pairs(*chapter_verse_ann_id_map_list):
    seg_pairs = {}

    for ch in chapter_verse_ann_id_map_list:
        chapter_verse_ann_id_map = chapter_verse_ann_id_map[pecha_id]




def main():
    parallel_pages = [Path("bodhicaryavatara-final/སྤྱོད་འཇུག་རྩ་འགྲེལ།_data/books/C01/སྤྱོད་འཇུག་རྩ་བ།-chapter-01.txt").read_text(),
    Path("bodhicaryavatara-final/སྤྱོད་འཇུག་རྩ་འགྲེལ།_data/books/C02/Thokme-chapter-01.txt").read_text(),
    Path("bodhicaryavatara-final/སྤྱོད་འཇུག་རྩ་འགྲེལ།_data/books/C03/Kunpal-chapter-01.txt").read_text()]
    pecha_ids = [get_initial_pecha_id() for i in range(3)]
    alignment_id = get_alignment_id()
    parse_usfm_pages(parallel_pages,pecha_ids,alignment_id)  

if __name__ == "__main__":
    main()
