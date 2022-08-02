from pathlib import Path
from openpecha.core.ids import get_base_id,get_initial_pecha_id
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
    pre_text = page[:first_chapter_start]
    chapter_verses_map.update({"pre_text":pre_text})
    return chapter_verses_map


def get_verses(text):
    verses_title_cont_map = {}
    verses = list(re.finditer(r"\v \d+",text))

    for index,cur_verse in enumerate(verses):
        verse_no = cur_verse.group()
        cur_verse_no_start,cur_verse_no_end = cur_verse.sapn()
        if index < len(verses)-1:
            next_verse = verses[index+1]
            next_verse_no_start,next_verse_no_end = next_verse.span()
            cur_verse_span = (cur_verse_no_end,next_verse_no_start)
        else:
            cur_verse_span = (cur_verse_no_end,len(text))

        start,end = cur_verse_span
        cur_verse_text = text[start:end]
        verses_title_cont_map.update({verse_no:cur_verse_text})  

    return verses_title_cont_map  



def parse_usfm_page(parallel_pages):
    
    for page in parallel_pages:
        chapter_verses_map = parse_chapter(page)
        create_opf(chapter_verses_map)



def create_opf(chapter_verses_map,pecha_id,base_id):
    opf_path = f"opf/{pecha_id}{pecha_id}.opf"
    opf = OpenPechaFS(path=opf_path)
    base_text = get_base_text(chapter_verses_map)
    bases = {base_id:base_text}
    layers = {base_id:{LayerEnum.segment:get_segment_layer(chapter_verses_map)}}




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
    char_walker = 0
    pre_text = chapter_verses_map["pre_text"]

    segment_annotation,char_walker = get_segment_annotation(pre_text,char_walker)
    segment_annotations.update(segment_annotation)
    for chapter in chapter_verses_map:
        if chapter == "pre_text":
            continue
        for verse in chapter_verses_map[chapter]:
            segment_annotation,char_walker = get_segment_annotation(chapter_verses_map[chapter][verse],char_walker)
            segment_annotations.update(segment_annotation)

    return segment_annotations         


def get_segment_annotation(text,char_walker):
    segment_annotation = {
            uuid4().hex:AnnBase(span=Span(start=char_walker, end=char_walker + len(text)))
        }

    return (segment_annotation,len(text)+2+char_walker)


def get_parallel_texts(dir):
    pass


if __name__ == "__main__":
    page = Path("bodhicaryavatara-final/སྤྱོད་འཇུག་རྩ་འགྲེལ།_data/books/C01/སྤྱོད་འཇུག་རྩ་བ།-chapter-01.txt").read_text()
    parse_chapter(page)    
