import os
import requests
from html.parser import HTMLParser


def parse_style(text: str):
    style = list(map(lambda x: x.strip(), text.split(";")))
    style = list(filter(lambda x: not x == '', style))

    if not len(style) == 1:
        raise RuntimeError(style)
    
    style_dict: dict[str, str] = {}
    for s in style:
        _s = list(map(lambda x: x.strip(), s.split(":")))
        tag, data = list(filter(lambda x: not x == '', _s))
        style_dict[tag] = data
    
    return style_dict


def parse_class(text: str):
    return text.split(" ")


def parse_span(attrs):
    if len(attrs) == 0:
        return None
    elif len(attrs) == 1:
        if attrs[0][0] == "style":
            if attrs[0][1] is None:
                raise RuntimeError(attrs)
            else:
                style = parse_style(attrs[0][1])
                if style["color"] == "black":
                    return None
                else:
                    return {"color": style["color"]}
        else:
            raise RuntimeError(attrs)
    else:
        raise RuntimeError(attrs)


def parse_div(attrs):
    if len(attrs) == 1:
        if attrs[0][0] == "class":
            if attrs[0][1] is None:
                raise RuntimeError(attrs)
            _class = parse_class(attrs[0][1])
            if len(_class) == 1:
                if _class[0] in ["ql-image", "ql-image-wrp", "ql-divider"]:
                    return None
                else:
                    raise RuntimeError(_class[0])
            else:
                raise RuntimeError(_class)
    else:
        raise RuntimeError(attrs)


def parse_img(attrs) -> str:
    if len(attrs) == 1:
        if attrs[0][0] == "src":
            if attrs[0][1] is None:
                raise RuntimeError(attrs)
            return attrs[0][1]
        else:
            raise RuntimeError(attrs[0])
    else:
        raise RuntimeError(attrs)


def parse_link(attrs) -> str:
    dict_attrs = dict(attrs)
    if len(dict_attrs) <= 2:
        if dict_attrs["href"] is None:
            raise RuntimeError(attrs)
        return dict_attrs["href"]
    else:
        raise RuntimeError(attrs)


def parse_have_style(attrs):
    _dict = dict(attrs)
    if len(_dict) == 0:
        return None
    elif len(_dict) == 1:
        if _dict["style"] is None:
            raise RuntimeError(attrs)
        else:
            style = parse_style(_dict["style"])
            if style["color"] == "black":
                return None
            else:
                return {"color": style["color"]}
    else:
        raise RuntimeError(attrs)


class MyHTMLParser(HTMLParser):
    def __init__(self, dst: str, *, convert_charrefs: bool = ...) -> None:
        super().__init__(convert_charrefs=convert_charrefs)
        self.md_text = ""
        self.skip_stack = []
        self.block_stack = []
        self.tmp_links = []
        self.tmp_inner_contents = []
        self.dst = dst
        if not self.dst.endswith("/"):
            self.dst += "/"
    
    def handle_starttag(self, tag, attrs):
        isSkip = False

        if tag == "p":
            isSkip = True
        elif tag == "span":
            span = parse_have_style(attrs)
            if span is None:
                isSkip = True
            else:
                self.md_text += f'<span style="color: {span["color"]}">'
        elif tag == "br":
            isSkip = None
            self.md_text += "\n\n"
        elif tag == "div":
            div = parse_div(attrs)
            if div is None:
                isSkip = True
            else:
                raise RuntimeError(div)
        elif tag == "img":
            isSkip = None
            img = parse_img(attrs)
            if isinstance(img, str):
                filename = img.split("/")[-1]
                if not os.path.exists(self.dst + 'attachments'):
                    os.mkdir(self.dst + 'attachments')
                path = self.dst + 'attachments/' + filename
                rel_path = 'attachments/' + filename
                if not os.path.exists(path):
                    res = s.get(img, stream=True)
                    with open(path, "wb") as f:
                        for chunk in res.iter_content(1024 * 512):
                            f.write(chunk)
                self.md_text += f"![{rel_path}]({rel_path})"
            else:
                raise RuntimeError(type(img), img)
        elif tag == "h1":
            self.md_text += "# "
        elif tag == "h2":
            self.md_text += "## "
        elif tag == "h3":
            self.md_text += "### "
        elif tag == "h4":
            self.md_text += "#### "
        elif tag == "h5":
            self.md_text += "#####"
        elif tag == "h6":
            self.md_text += "###### "
        elif tag == "strong":
            style = parse_have_style(attrs)
            if style is None:
                isSkip = True
            else:
                self.md_text += f'<span style="color: {style["color"]}">'
            self.md_text += "**"
        elif tag == "a":
            link = parse_link(attrs)
            self.tmp_links.append(link)
            self.md_text += "["
        else:
            raise RuntimeError(tag)

        self.tmp_inner_contents.append(tag)

        if isSkip is not None:
            self.skip_stack.append(isSkip)

        # print("Encountered a start tag:", tag, attrs)

    def handle_endtag(self, tag):
        isSkip = self.skip_stack.pop()
        
        if tag == "strong":
            self.md_text += "**"
        elif tag == "a":
            self.md_text += f"]({self.tmp_links.pop()})"
        elif not isSkip:
            self.md_text += f"</{tag}>"
            
        if len(self.skip_stack) == 0:
            if not self.tmp_inner_contents == ["p", "br"]:
                self.md_text += "\n\n"
            self.tmp_inner_contents.clear()

        # print("Encountered an end tag :", tag)

    def handle_data(self, data):
        data.replace("\t", "    ")
        self.md_text += data

        # print(data)


with requests.Session() as s:
    post_id = "14184074"
    if not os.path.exists(post_id):
        os.mkdir(post_id)

    parser = MyHTMLParser("14184074/")

    s.headers = {"User-Agent": ""}

    res = s.get("https://bbs-api-os.hoyolab.com/community/post/wapi/getPostFull",
                params={"post_id": post_id, "read": "1"})
    data = res.json()["data"]
    parser.feed(data["post"]["post"]["content"])
    with open(f"{post_id}/test2.md", "w", encoding='utf-8') as f:
        f.write(parser.md_text)
