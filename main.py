import os
from typing import Dict, Union, List, Tuple
import warnings
import requests
from html.parser import HTMLParser
import re

from tqdm import tqdm


ARTICLE_FILE_NAME = "article"


class Subscriptable():
    def __init__(self) -> None:
        self.dict: dict[str, str] = {}
    
    def __contains__(self, key):
        return True if key in self.dict else False
    
    def __getitem__(self, key):
        if key not in self.dict:
            return KeyError(key)
        return self.dict[key]


class Style(Subscriptable):
    def __init__(self, string: str) -> None:
        super().__init__()
        self.parse_style(string)

    def parse_style(self, text: str):
        style = list(map(lambda x: x.strip(), text.split(";")))
        style = list(filter(lambda x: not x == '', style))
        
        for s in style:
            _s = list(map(lambda x: x.strip(), s.split(":")))
            tag, data = list(filter(lambda x: not x == '', _s))
            self.dict[tag] = data


class Attributes():
    def __init__(self) -> None:
        self.style: Union[Style, None] = None
        self.href: Union[str, None] = None
        self.cls: Union[List[str], None] = None
        self.src: Union[str, None] = None
        self.alt: Union[str, None] = None


def parse_attributes(attrs: List[Tuple[str, Union[str, None]]],
                     allow_attributes: Union[List[str], None] = None):
    returns = Attributes()
    if allow_attributes is None:
        allow_attributes = ["style", "href", "class", "src", "alt"]
    
    for k, v in dict(attrs).items():
        if k not in allow_attributes:
            raise RuntimeError(f'{k} is not allowd!')
        if v is None:
            if   k == "":
                pass
        else:
            if   k == "style":
                returns.style = Style(v)
            elif k == "href":
                returns.href = v
            elif k == "class":
                returns.cls = v.split(" ")
            elif k == "src":
                returns.src = v
            elif k == "alt":
                returns.alt = v
    return returns


class MyHTMLParser(HTMLParser):
    def __init__(self, dst: str, session: requests.Session,
                 *, convert_charrefs: bool = ...) -> None:
        super().__init__(convert_charrefs=convert_charrefs)
        self.md_text = ""
        self.skip_stack: List[bool] = []
        self.tmp_links: List[str] = []
        self.tmp_inner_contents: List[str] = []
        
        self.links: List[str] = []
        self.linked_post_ids: List[str] = []
        self.images: Dict[str, str] = {}

        self.dst = dst
        self.session = session

        if not self.dst.endswith("/"):
            self.dst += "/"
    
    def span_begin(self, attrs: List[Tuple[str, Union[str, None]]]) -> bool:
        isSkip = False
        span = parse_attributes(attrs, ['style'])
        if span.style is None or span.style["color"] == "black":
            isSkip = True
        else:
            self.md_text += f'<span style="color: {span.style["color"]}">'
        
        return isSkip
    
    def br_begin(self, attrs: List[Tuple[str, Union[str, None]]]) -> None:
        parse_attributes(attrs, [])  # no attribute check.
        self.md_text += "\n\n"
        return None

    def div_begin(self, attrs: List[Tuple[str, Union[str, None]]]) -> bool:
        div = parse_attributes(attrs, ["class"])
        if div.cls is None:
            raise RuntimeError
        
        if all(c in ["ql-image", "ql-image-wrp", "ql-divider", "ql-align-center"] for c in div.cls):
            return True
        else:
            raise RuntimeError(div.cls)
    
    def img_begin(self, attrs: List[Tuple[str, Union[str, None]]]) -> None:
        img = parse_attributes(attrs, ["src", "alt"])
        if isinstance(img.src, str):
            filename = img.src.split("/")[-1]
            rel_path = 'attachments/' + filename

            self.images[filename] = img.src
            
            self.md_text += f"![{img.alt if img.alt else img.src}]({rel_path})"
        else:
            raise RuntimeError(type(img.src), img.src)
        
        return None
    
    def head_begin(self, attrs: List[Tuple[str, Union[str, None]]], level: int) -> bool:
        parse_attributes(attrs, [])  # no attribute check.
        self.md_text += "#" * level + " "
        return True
    
    def strong_begin(self, attrs: List[Tuple[str, Union[str, None]]]) -> bool:
        strong = parse_attributes(attrs, ["style"])
        if strong.style is None or strong.style["color"] == "black":
            isSkip = True
        else:
            self.md_text += f'<span style="color: {strong.style["color"]}">'
            isSkip = False
        self.md_text += "**"
        return isSkip
    
    def anchor_begin(self, attrs) -> bool:
        anchor = parse_attributes(attrs, ["href", "style"])
        if anchor.href is None:
            raise ValueError('There are no "href"! Check html.')
        if anchor.href.startswith("https://www.hoyolab.com/article/"):
            match = re.search(r'(?<=article\/)[0-9]+', anchor.href)
            if not match:
                raise ValueError('Invaild hoyolab post url!')
            link = '../' + match.group() + '/' + ARTICLE_FILE_NAME

            self.linked_post_ids.append(match.group())
        else:
            warnings.warn("hoyolabの投稿以外のリンクが発見されました。 > " + anchor.href)
            link = anchor.href
        self.tmp_links.append(link)
        self.md_text += "["
        return False

    def handle_starttag(self, tag, attrs):
        if   tag == "p":
            pass
            self.skip_stack.append(True)
        elif tag == "span":
            isSkip = self.span_begin(attrs)
            self.skip_stack.append(isSkip)
        elif tag == "br":
            self.br_begin(attrs)
        elif tag == "div":
            self.div_begin(attrs)
            self.skip_stack.append(True)
        elif tag == "img":
            self.img_begin(attrs)
        elif tag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            self.head_begin(attrs, int(tag[1:2]))
            self.skip_stack.append(True)
        elif tag == "strong":
            isSkip = self.strong_begin(attrs)
            self.skip_stack.append(isSkip)
        elif tag == "a":
            self.anchor_begin(attrs)
            self.skip_stack.append(False)
        else:
            raise RuntimeError(tag)

        self.tmp_inner_contents.append(tag)

        # if isSkip is not None:
        #     self.skip_stack.append(isSkip)

        # print("Encountered a start tag:", tag, attrs)

    def handle_endtag(self, tag):
        isSkip = self.skip_stack.pop()
        
        if tag == "strong":
            self.md_text += "**"
            if not isSkip:
                self.md_text += "</span>"
        elif tag == "a":
            link = self.tmp_links.pop()
            self.links.append(link)
            self.md_text += f"]({link})"
        elif not isSkip:
            self.md_text += f"</{tag}>"
        
        if len(self.skip_stack) == 0:
            if not self.tmp_inner_contents == ["p", "br"]:
                self.md_text += "\n\n"
            self.tmp_inner_contents.clear()

    def handle_data(self, data):
        data = data.replace("\xa0", " ")
        self.md_text += data
    
    def get_linked_post_ids(self):
        linked_post_ids = []
        for link in self.links:
            if link.startswith('https://www.hoyolab.com/article/'):
                match = re.search(r'(?<=article\/)[0-9]+', link)
                if match is None:
                    raise ValueError("invaild hoyolab article url!")
                linked_post_ids.append(match.group())
        return linked_post_ids


def download_images(session: requests.Session, dst: str,
                    filename_stc: Dict[str, str], with_tqdm=True):
    if not dst.endswith('/'):
        dst += '/'
    
    if with_tqdm:
        tq = tqdm(filename_stc.items())
    else:
        tq = filename_stc.items()

    for filename, src in tq:
        if not os.path.exists(dst + 'attachments'):
            os.mkdir(dst + 'attachments')
        path = dst + 'attachments/' + filename

        if not os.path.exists(path):
            res = session.get(src, stream=True)
            with open(path, "wb") as f:
                for chunk in res.iter_content(1024 * 512):
                    f.write(chunk)


def save_hoyolab_post(post_id: str):
    with requests.Session() as s:
        if not os.path.exists(post_id):
            os.mkdir(post_id)

        DST = "posts/" + post_id + "/"
        parser = MyHTMLParser(post_id + "/", s)

        s.headers = {"User-Agent": ""}  # type: ignore
        res = s.get("https://bbs-api-os.hoyolab.com/community/post/wapi/getPostFull",
                    params={"post_id": post_id, "read": "1"})
        data = res.json()["data"]
        # with open("test.html", "wb") as f:
        #     f.write(res.content)
        parser.feed(data["post"]["post"]["content"])
        download_images(s, DST, parser.images, with_tqdm=True)
        
        with open(DST + f"{ARTICLE_FILE_NAME}.md", "w", encoding='utf-8') as f:
            f.write(parser.md_text)
        
        print(parser.linked_post_ids)


for id in ['13783075', '14091045', '14216127', '7955164', '13809367', '14155947', '14156515', '12312126', '12304317', '14156063', '14156290', '8471110', '8483830', '14214242', '9989311', '9423533', '14183709', '14184074', '14184039', '14183919', '14184353', '14184589', '14184841']:
    save_hoyolab_post(id)
