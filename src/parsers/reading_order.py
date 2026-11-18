"""Geometry-only reading view. Never rewrite original blocks or raw offsets."""
from collections import defaultdict
from dataclasses import dataclass
import re

CAPTION_PREFIX = re.compile(r'^\s*(?:fig(?:ure)?\.?|table|scheme)\s*(?:S?\d+|[IVXLCDM]+)\b', re.I)


def is_caption(block, hints):
    if CAPTION_PREFIX.match(block.text):
        return True
    hint = (hints or {}).get((block.block_id, getattr(block,'raw_start',0)), {})
    return (len(block.text.strip()) < 200 and hint.get('after_visual', False)
            and not hint.get('bold', False) and len(block.text.split()) >= 3)


@dataclass(frozen=True)
class ReadingBlock:
    block_id:str
    page_number:int
    text:str
    bbox:object
    raw_start:int
    raw_end:int


def split_columns(block,hints):
    lines=[];offset=0
    for line in block.text.splitlines(keepends=True):
        hint=(hints or {}).get((block.block_id,offset),{})
        lines.append((offset,offset+len(line),hint.get('bbox')));offset+=len(line)
    width=(hints or {}).get((block.block_id,0),{}).get('page_width',600.)
    left=[b for _,_,b in lines if b and (b[0]+b[2])/2<width*.46]
    right=[b for _,_,b in lines if b and (b[0]+b[2])/2>width*.54]
    if not left or not right or min(b[0] for b in right)-max(b[2] for b in left)<width*.025:
        return (ReadingBlock(block.block_id,block.page_number,block.text,block.bbox,0,len(block.text)),)
    groups=[]
    for a,z,bbox in lines:
        side=int((bbox[0]+bbox[2])/2>=width*.5) if bbox else -1
        if groups and groups[-1][0]==side:groups[-1][2]=z;groups[-1][3].append(bbox)
        else:groups.append([side,a,z,[bbox]])
    return tuple(ReadingBlock(block.block_id,block.page_number,block.text[a:z],
        (min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)),a,z)
        for _,a,z,boxes in groups)


def role_key(block):return block.block_id,block.raw_start,block.raw_end


def ordered_blocks(paper, hints=None):
    """Return ordered raw objects plus roles; page order is never changed."""
    pages = defaultdict(list)
    removed = {w.removeprefix('removed_block:') for w in paper.warnings if w.startswith('removed_block:')}
    roles = {}
    for raw in paper.raw_blocks:
        for block in split_columns(raw,hints):
            pages[block.page_number].append(block)
            if block.block_id in removed:
                roles[role_key(block)] = 'margin'
            elif is_caption(block, hints):
                roles[role_key(block)] = 'caption'
    # Captions can be fragmented by formula/font runs into several raw blocks.
    # Continue only along the same column, in smaller-than-body type, from an
    # explicitly recognized caption. Do not absorb normal-sized prose.
    for page_blocks in pages.values():
        for block in sorted(page_blocks,key=lambda b:b.bbox[1] if b.bbox else 0):
            if role_key(block) in roles or not block.bbox:continue
            h=(hints or {}).get((block.block_id,block.raw_start),{})
            if not h or h.get('size',99)>=h.get('body_size',10)*.96:continue
            for caption in page_blocks:
                if roles.get(role_key(caption))!='caption' or not caption.bbox:continue
                a,b=caption.bbox,block.bbox
                overlap=min(a[2],b[2])-max(a[0],b[0])
                if overlap>min(a[2]-a[0],b[2]-b[0])*.45 and -5<=b[1]-a[3]<=28:
                    roles[role_key(block)]='caption';break
    ordered = []
    for page in sorted(pages):
        original = pages[page]
        body = [b for b in original if role_key(b) not in roles]
        if body and all(b.bbox is not None for b in body):
            width = (hints or {}).get((body[0].block_id, 0), {}).get('page_width', 600.)
            def center(b): return (b.bbox[0]+b.bbox[2])/2
            left = [b for b in body if center(b)<width*.46 and b.bbox[2]-b.bbox[0]<width*.56 and len(b.text.strip())>=5]
            right = [b for b in body if center(b)>width*.54 and b.bbox[2]-b.bbox[0]<width*.56 and len(b.text.strip())>=5]
            pairs = [(l,r) for l in left for r in right if l.bbox[2]+width*.025<r.bbox[0]
                     and min(l.bbox[3],r.bbox[3])>max(l.bbox[1],r.bbox[1])]
            sparse_columns = bool(pairs and any(len(b.text)>220 and len(b.text.splitlines())>=5 for b in left) and any(len(b.text)>220 and len(b.text.splitlines())>=5 for b in right))
            if (len(left)>=2 and len(right)>=2 and len(pairs)>=2) or sparse_columns:
                wide = sorted([b for b in body if b.bbox[0]<width*.35 and b.bbox[2]>width*.65], key=lambda b:b.bbox[1])
                narrow = [b for b in body if b not in wide]
                # A spanning title/abstract separates vertical bands; within each band
                # the complete left column precedes the complete right column.
                for separator in wide:
                    before = [b for b in narrow if b.bbox[1]<separator.bbox[1]]
                    ordered.extend(sorted(before,key=lambda b:(center(b)>=width*.5,b.bbox[1],b.bbox[0])))
                    narrow = [b for b in narrow if b not in before]
                    ordered.append(separator)
                ordered.extend(sorted(narrow,key=lambda b:(center(b)>=width*.5,b.bbox[1],b.bbox[0])))
            else:
                ordered.extend(sorted(body,key=lambda b:(b.bbox[1],b.bbox[0])))
        else:
            ordered.extend(body)
        # Excluded objects retain full coverage but cannot move section boundaries.
        ordered.extend(b for b in original if role_key(b) in roles)
    return tuple(ordered), roles
