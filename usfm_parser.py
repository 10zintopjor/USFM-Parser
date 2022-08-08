from pathlib import Path
from openpecha.core.ids import get_base_id,get_initial_pecha_id,get_alignment_id
from datetime import datetime
from openpecha.core.layer import Layer, LayerEnum
from openpecha.core.pecha import OpenPechaFS 
from openpecha.core.metadata import InitialPechaMetadata,InitialCreationType
from openpecha.core.annotation import AnnBase, Span
from uuid import uuid4
import re
import yaml

def toyaml(dict):
    return yaml.safe_dump(dict, sort_keys=False, allow_unicode=True)

def from_yaml(yml_path):
    return yaml.safe_load(yml_path.read_text(encoding="utf-8"))

def parse_chapter(page):
    chapters = list(re.finditer(r"\\c \d+",page))
    chapter_verses_map = {}
    chapter_no_title_map = {}

    for index,cur_chapter in enumerate(chapters):
        chapter_no = cur_chapter.group()
        cur_chapter_start,cur_chapter_end = cur_chapter.span()
        chapter_title = get_chapter_title(page,cur_chapter_end)

        if index < len(chapters)-1:
            next_chapter = chapters[index+1]
            next_chapter_start,next_chapter_end = next_chapter.span()
            cur_chapter_span = (cur_chapter_end,next_chapter_start)
        else:
            cur_chapter_span = (cur_chapter_end,len(page))

        start,end = cur_chapter_span
        cur_text = page[start:end]
        verses_no_cont_map = get_verses(cur_text)
        chapter_verses_map.update({chapter_no:verses_no_cont_map})
        chapter_no_title_map.update({chapter_no:chapter_title})

    first_chapter_start,_ = chapters[0].span()
    pre_text = remove_usfm_ann(page[:first_chapter_start])
    chapter_verses_map.update({"pre_text":pre_text})
    
    return chapter_verses_map,chapter_no_title_map

def get_chapter_title(page,start):
    match = re.search(r"\\v \d+",page)
    end = match.end()
    title = remove_usfm_ann(page[start:end])
    return title

def get_verses(text):
    verses_no_cont_map = {}
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
        verses_no_cont_map.update({verse_no:clean_verse_text})  

    return verses_no_cont_map  

def remove_usfm_ann(ann_text):
    clean_text = re.sub(r"\\+\w+\s?\d?","",ann_text)
    return clean_text.strip()


def create_opf(chapter_verses_map,chapter_no_title_map,pecha_id,base_id):
    opf_path = f"opf/{pecha_id}/{pecha_id}.opf"
    opf = OpenPechaFS(path=opf_path)
    base_text = get_base_text(chapter_verses_map,chapter_no_title_map)
    bases = {base_id:base_text}
    seg_layer,aligned_verse_ann_id = get_segment_layer(chapter_verses_map,chapter_no_title_map)
    layers = {base_id:{LayerEnum.segment:seg_layer}}

    opf.base = bases
    opf.layers = layers
    opf.save_base()
    opf.save_layers()

    return aligned_verse_ann_id



def get_base_text(chapter_verses_map,chapter_no_title_map):
    pre_text = chapter_verses_map["pre_text"]
    base_text = pre_text +"\n\n"
    for chapter in chapter_verses_map:
        if chapter == "pre_text":
            continue
        elif chapter_no_title_map[chapter] != "":
            base_text += chapter_no_title_map[chapter]+"\n\n"
        for verse in chapter_verses_map[chapter]:
            base_text+= chapter_verses_map[chapter][verse]+"\n\n"
    
    return base_text


def get_segment_layer(chapter_verses_map,chapter_no_title_map):
    segment_annotations = {}
    aligned_verse_ann_id = []

    char_walker = 0
    pre_text = chapter_verses_map["pre_text"]

    segment_annotation,char_walker,_ = get_segment_annotation(pre_text,char_walker)
    segment_annotations.update(segment_annotation)
    for chapter in chapter_verses_map:
        if chapter == "pre_text":
            continue
        elif chapter_no_title_map[chapter] != "":
            segment_annotation,char_walker,_ = get_segment_annotation(chapter_no_title_map[chapter],char_walker)
            segment_annotations.update(segment_annotation)
        for verse in chapter_verses_map[chapter]:
            segment_annotation,char_walker,ann_id = get_segment_annotation(chapter_verses_map[chapter][verse],char_walker)
            segment_annotations.update(segment_annotation)
            aligned_verse_ann_id.append(ann_id)
    segment_layer = Layer(annotation_type=LayerEnum.segment,annotations=segment_annotations)
    
    return segment_layer,aligned_verse_ann_id      


def get_segment_annotation(text,char_walker):
    ann_id = uuid4().hex
    segment_annotation = {
           ann_id:AnnBase(span=Span(start=char_walker, end=char_walker + len(text)))
        }

    return (segment_annotation,len(text)+2+char_walker,ann_id)

def parse_usfm_pages(parallel_pages,pecha_ids,alignment_id):
    base_id = get_base_id()
    aligned_seg_pairs = []
    for page,pecha_id in zip(parallel_pages,pecha_ids):
        chapter_verses_map,chapter_no_title_map = parse_chapter(page)
        aligned_verse_ann_id = create_opf(chapter_verses_map,chapter_no_title_map,pecha_id,base_id)
        aligned_seg_pairs = get_aligned_seg_pairs(pecha_id,aligned_seg_pairs,aligned_verse_ann_id)
    create_opa(alignment_id,aligned_seg_pairs,pecha_ids,base_id)


def get_aligned_seg_pairs(pecha_id,aligned_seg_pairs,aligned_verse_ann_id):
    aligned_seg_pairs_moded = []
    if not aligned_seg_pairs:
        for ann_id in aligned_verse_ann_id:
            pecha_id_seg_id = {}
            pecha_id_seg_id.update({pecha_id:ann_id})
            aligned_seg_pairs_moded.append(pecha_id_seg_id)
    else:
        for seg_pair,ann_id in zip(aligned_seg_pairs,aligned_verse_ann_id):
            seg_pair.update({pecha_id:ann_id})
            aligned_seg_pairs_moded.append(seg_pair)

    return aligned_seg_pairs_moded                

def create_opa(alignment_id,aligned_seg_pairs,pecha_ids,base_id):
    alignments = {}
    seg_annotations = {}
    segment_sources = get_segment_sources(pecha_ids)
    for seg_pair in aligned_seg_pairs:
        seg_annotations.update({uuid4().hex:seg_pair})
    alignments.update({"segment_sources":segment_sources})
    alignments.update({"segment_pairs":seg_annotations})
    alignments_yml = toyaml(alignments)
    Path(f"./opa/{alignment_id}/{alignment_id}.opa/").mkdir(parents=True, exist_ok=True)
    Path(f"./opa/{alignment_id}/{alignment_id}.opa/Alignment.yml").write_text(alignments_yml)

def get_segment_sources(pecha_ids):
    segment_sources = {}
    for pecha_id in pecha_ids:
        segment_sources.update({pecha_id:{
            "type":"origin_type",
            "language":"bo"
        }})

    return segment_sources


def main():
    parallel_pages = [Path("bodhicaryavatara-final/སྤྱོད་འཇུག་རྩ་འགྲེལ།_data/books/C01/སྤྱོད་འཇུག་རྩ་བ།-chapter-01.txt").read_text(),
    Path("bodhicaryavatara-final/སྤྱོད་འཇུག་རྩ་འགྲེལ།_data/books/C02/Thokme-chapter-01.txt").read_text(),
    Path("bodhicaryavatara-final/སྤྱོད་འཇུག་རྩ་འགྲེལ།_data/books/C03/Kunpal-chapter-01.txt").read_text()]
    pecha_ids = [get_initial_pecha_id() for i in range(3)]
    alignment_id = get_alignment_id()
    parse_usfm_pages(parallel_pages,pecha_ids,alignment_id)  

if __name__ == "__main__":
    main()
