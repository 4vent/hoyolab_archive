import os
from typing import Literal, Union
import requests
from html.parser import HTMLParser


# def parse_class(text: str):
#     return text.split(" ")


# def parse_span(attrs: list[tuple[str, Union[str, None]]]):
#     if len(attrs) == 0:
#         return None
#     elif len(attrs) == 1:
#         if attrs[0][0] == "style":
#             if attrs[0][1] is None:
#                 raise RuntimeError(attrs)
#             else:
#                 style = parse_style(attrs[0][1])
#                 if style["color"] == "black":
#                     return None
#                 else:
#                     return {"color": style["color"]}
#         else:
#             raise RuntimeError(attrs)
#     else:
#         raise RuntimeError(attrs)


# def parse_div(attrs: list[tuple[str, Union[str, None]]]):
#     if len(attrs) == 1:
#         if attrs[0][0] == "class":
#             if attrs[0][1] is None:
#                 raise RuntimeError(attrs)
#             _class = parse_class(attrs[0][1])
#             if len(_class) == 1:
#                 if _class[0] in ["ql-image", "ql-image-wrp", "ql-divider"]:
#                     return None
#                 else:
#                     raise RuntimeError(_class[0])
#             else:
#                 raise RuntimeError(_class)
#     else:
#         raise RuntimeError(attrs)


# def parse_img(attrs: list[tuple[str, Union[str, None]]]) -> str:
#     if len(attrs) == 1:
#         if attrs[0][0] == "src":
#             if attrs[0][1] is None:
#                 raise RuntimeError(attrs)
#             return attrs[0][1]
#         else:
#             raise RuntimeError(attrs[0])
#     else:
#         raise RuntimeError(attrs)


# def parse_link(attrs: list[tuple[str, Union[str, None]]]) -> str:
#     dict_attrs = dict(attrs)
#     if len(dict_attrs) <= 2:
#         if dict_attrs["href"] is None:
#             raise RuntimeError(attrs)
#         return dict_attrs["href"]
#     else:
#         raise RuntimeError(attrs)


# def parse_have_style(attrs: list[tuple[str, Union[str, None]]]):
#     _dict = dict(attrs)
#     if len(_dict) == 0:
#         return None
#     elif len(_dict) == 1:
#         if _dict["style"] is None:
#             raise RuntimeError(attrs)
#         else:
#             style = parse_style(_dict["style"])
#             if style["color"] == "black":
#                 return None
#             else:
#                 return {"color": style["color"]}
#     else:
#         raise RuntimeError(attrs)


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
        self.cls: Union[list[str], None] = None
        self.src: Union[str, None] = None


def parse_attributes(attrs: list[tuple[str, Union[str, None]]],
                     allow_attributes: Union[list[str], None] = None):
    returns = Attributes()
    if allow_attributes is None:
        allow_attributes = ["style", "href", "class", "src"]
    
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
    return returns


class MyHTMLParser(HTMLParser):
    def __init__(self, dst: str, session: requests.Session,
                 *, convert_charrefs: bool = ...) -> None:
        super().__init__(convert_charrefs=convert_charrefs)
        self.md_text = ""
        self.skip_stack = []
        self.block_stack = []
        self.tmp_links = []
        self.tmp_inner_contents = []

        self.dst = dst
        self.session = session

        if not self.dst.endswith("/"):
            self.dst += "/"
    
    def span_begin(self, attrs: list[tuple[str, Union[str, None]]]) -> Literal[True, False]:
        isSkip = False
        span = parse_attributes(attrs, ['style'])
        if span.style is None or span.style["color"] == "black":
            isSkip = True
        else:
            self.md_text += f'<span style="color: {span.style["color"]}">'
        
        return isSkip
    
    def br_begin(self, attrs: list[tuple[str, Union[str, None]]]) -> None:
        parse_attributes(attrs, [])  # no attribute check.
        self.md_text += "\n\n"
        return None

    def div_begin(self, attrs: list[tuple[str, Union[str, None]]]) -> Literal[True]:
        div = parse_attributes(attrs, ["class"])
        if div.cls is None:
            raise RuntimeError
        
        if not len(div.cls) == 1:
            raise RuntimeError(div.cls)
        else:
            if div.cls[0] in ["ql-image", "ql-image-wrp", "ql-divider"]:
                return True
            else:
                raise RuntimeError(div.cls[0])
    
    def img_begin(self, attrs: list[tuple[str, Union[str, None]]]) -> None:
        img = parse_attributes(attrs, ["src"])
        if isinstance(img.src, str):
            filename = img.src.split("/")[-1]
            if not os.path.exists(self.dst + 'attachments'):
                os.mkdir(self.dst + 'attachments')
            path = self.dst + 'attachments/' + filename
            rel_path = 'attachments/' + filename
            if not os.path.exists(path):
                res = self.session.get(img.src, stream=True)
                with open(path, "wb") as f:
                    for chunk in res.iter_content(1024 * 512):
                        f.write(chunk)
            if rel_path == "attachments/a1e15cc426cee40fad9041b6366bfe97_9052374612559652330.jpg":
                print("", end="")
            self.md_text += f"![{rel_path}]({rel_path})"
        else:
            raise RuntimeError(type(img.src), img.src)
        
        return None
    
    def head_begin(self, attrs: list[tuple[str, Union[str, None]]], level: int) -> Literal[True]:
        parse_attributes(attrs, [])  # no attribute check.
        self.md_text += "#" * level + " "
        return True
    
    def strong_begin(self, attrs: list[tuple[str, Union[str, None]]]) -> Literal[True, False]:
        strong = parse_attributes(attrs, ["style"])
        if strong.style is None or strong.style["color"] == "black":
            isSkip = True
        else:
            self.md_text += f'<span style="color: {strong.style["color"]}">'
            isSkip = False
        self.md_text += "**"
        return isSkip
    
    def anchor_begin(self, attrs) -> Literal[False]:
        anchor = parse_attributes(attrs, ["href", "style"])
        self.tmp_links.append(anchor.href)
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
            self.md_text += f"]({link})"
        elif not isSkip:
            self.md_text += f"</{tag}>"
        
        skip_stack = self.skip_stack
        if len(self.skip_stack) == 0:
            if not self.tmp_inner_contents == ["p", "br"]:
                self.md_text += "\n\n"
            self.tmp_inner_contents.clear()

    def handle_data(self, data):
        if "\t" in data:
            print("")
        data = data.replace("\t", "    ")
        self.md_text += data


def save_hoyolab_post(post_id: str):
    with requests.Session() as s:
        if not os.path.exists(post_id):
            os.mkdir(post_id)

        parser = MyHTMLParser("14184074/", s)

        s.headers = {"User-Agent": ""}  # type: ignore
        res = s.get("https://bbs-api-os.hoyolab.com/community/post/wapi/getPostFull",
                    params={"post_id": post_id, "read": "1"})
        data = res.json()["data"]
        with open("test.html", "wb") as f:
            f.write(res.content)
        parser.feed(data["post"]["post"]["content"])
        with open(f"{post_id}/test2.md", "w", encoding='utf-8') as f:
            f.write(parser.md_text)


save_hoyolab_post("14184074")