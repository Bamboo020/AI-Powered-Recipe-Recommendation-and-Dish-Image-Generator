"""Local vision suggestions for visible ingredients, always awaiting human confirmation."""
import base64
import binascii
from io import BytesIO
import os
import re
from threading import Lock
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field
from .services import AIUnavailable

VISION_INGREDIENTS = ['egg','tomato','potato','onion','garlic','carrot','broccoli','cabbage','spinach','lettuce','cucumber','bell pepper','chili pepper','mushroom','zucchini','eggplant','corn','peas','green beans','scallion','ginger','chicken','beef','pork','fish','shrimp','tofu','cheese','milk','yogurt','butter','bread','noodles','pasta','raw rice','cooked rice','rice (state unknown)','oats','lentils','beans','apple','banana','lemon','orange','avocado']
_lock = Lock()


class VisibleIngredient(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: Literal[tuple(VISION_INGREDIENTS)]
    certainty: Literal['likely','uncertain']
    state: Literal['raw','cooked','unknown']


class PhotoFinding(BaseModel):
    model_config = ConfigDict(extra='forbid')
    photo_kind: Literal['ingredients','prepared_dish','non_food','unclear']
    ingredients: list[VisibleIngredient] = Field(max_length=15)


class PhotoBatch(BaseModel):
    images: list[str] = Field(min_length=1,max_length=3)


def validate_photo(encoded):
    from PIL import Image, ImageOps, UnidentifiedImageError
    if not isinstance(encoded,str) or len(encoded)>7*1024*1024:
        raise ValueError('Each photo must be a base64 image under 5 MB')
    try:
        raw=base64.b64decode(encoded,validate=True)
    except (binascii.Error,ValueError) as exc:
        raise ValueError('Invalid image encoding') from exc
    if len(raw)>5*1024*1024:
        raise ValueError('Each photo must be under 5 MB')
    try:
        with Image.open(BytesIO(raw)) as image:
            if image.format not in ('JPEG','PNG','WEBP') or image.width*image.height>16_000_000:
                raise ValueError('Use JPG, PNG or WebP photos up to 16 megapixels')
            image.load()
            image=ImageOps.exif_transpose(image).convert('RGB')
            image.thumbnail((1024,1024))
            output=BytesIO();image.save(output,format='JPEG',quality=85)
            return base64.b64encode(output.getvalue()).decode()
    except (UnidentifiedImageError,OSError,Image.DecompressionBombError) as exc:
        raise ValueError('The image could not be decoded') from exc


def parse_description(description):
    if not isinstance(description,str) or len(description)>3000:
        raise ValueError('Invalid vision description')
    text=description.lower()
    if re.search(r'\b(non-food|no food|not food)\b',text):
        return PhotoFinding(photo_kind='non_food',ingredients=[])
    # Conservative vocabulary mapping, not object detection or calibrated probabilities.
    names=[]
    for name in VISION_INGREDIENTS:
        if 'rice' in name:
            continue
        pattern=r'\b'+re.escape(name)+r'(?:s|es)?\b'
        for match in re.finditer(pattern,text):
            context=text[max(0,match.start()-35):match.start()]
            if not re.search(r'\b(no|not|without|possibly|maybe|might)\b',context):
                names.append(name);break
    if re.search(r'\brice\b',text):
        names.append('raw rice' if re.search(r'\b(raw|uncooked) rice\b',text) else 'cooked rice' if re.search(r'\bcooked rice\b',text) else 'rice (state unknown)')
    prepared=bool(re.search(r'\b(dish|cooked|fried|scrambled|roasted|baked|boiled|omelette|pizza|soup|sandwich|salad|stew)\b',text))
    kind='prepared_dish' if prepared else 'ingredients' if names else 'unclear'
    return PhotoFinding(photo_kind=kind,ingredients=[VisibleIngredient(name=name,certainty='uncertain',state='unknown') for name in dict.fromkeys(names)][:15])


def identify_ingredients(images):
    # Validate every image before running inference; strip EXIF and bound model input resolution.
    prepared=[validate_photo(value) for value in images]
    model=os.getenv('OLLAMA_VISION_MODEL')
    if not model:
        raise AIUnavailable('Ingredient vision is not configured. You can still enter ingredients manually.')
    if not _lock.acquire(blocking=False):
        raise AIUnavailable('Ingredient vision is busy. Please try again shortly.')
    photos=[]
    try:
        for index,encoded in enumerate(prepared):
            try:
                response=httpx.post(os.getenv('OLLAMA_BASE_URL','http://127.0.0.1:11434').rstrip('/')+'/api/chat',json={
                    'model':model,'stream':False,'keep_alive':'0s',
                    'messages':[{'role':'user','content':'Name only the foods that are visible in this image.','images':[encoded]}],
                    'options':{'temperature':0,'num_predict':180}},timeout=httpx.Timeout(90,connect=5))
                response.raise_for_status()
                description=response.json()['message']['content']
                finding=parse_description(description)
                photos.append({'photo_index':index+1,'status':'completed',**finding.model_dump()})
            except (httpx.HTTPError,ValueError,KeyError,TypeError):
                photos.append({'photo_index':index+1,'status':'unavailable','photo_kind':'unclear','ingredients':[],'message':'This photo could not be analyzed reliably. Please enter or correct its ingredients manually.'})
        return {'photos':photos,'provider':'ollama','model':model,'requires_confirmation':True,
                'status':'completed' if all(p['status']=='completed' for p in photos) else 'partial_or_unavailable',
                'notice':'Suggestions may be wrong or incomplete. Confirm ingredient names and cooking state before searching recipes. Photos cannot verify food safety, freshness, hidden allergens or quantities.'}
    finally:
        _lock.release()
