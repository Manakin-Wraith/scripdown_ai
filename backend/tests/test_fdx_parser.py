import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.fdx_parser import _read_fdx


MINIMAL_FDX = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<FinalDraft DocumentType="Script" Template="No" Version="5">
  <Content>
    <Paragraph Type="Scene Heading" Number="1">
      <SceneProperties Length="1/8" Page="1" Title=""/>
      <Text>INT. COFFEE SHOP - DAY</Text>
    </Paragraph>
    <Paragraph Type="Action">
      <Text>John sips his coffee.</Text>
    </Paragraph>
    <Paragraph Type="Character">
      <Text>JOHN</Text>
    </Paragraph>
    <Paragraph Type="Dialogue">
      <Text>Morning.</Text>
    </Paragraph>
  </Content>
  <TitlePage>
    <Content>
      <Paragraph><Text>MY GREAT SCRIPT</Text></Paragraph>
      <Paragraph><Text>Written by Jane Doe</Text></Paragraph>
    </Content>
  </TitlePage>
</FinalDraft>
"""


def _write_fdx(tmp_path, xml):
    p = tmp_path / "script.fdx"
    p.write_text(xml, encoding="utf-8")
    return str(p)


def test_read_fdx_returns_content_and_titlepage(tmp_path):
    path = _write_fdx(tmp_path, MINIMAL_FDX)
    content, titlepage = _read_fdx(path)

    types = [p["type"] for p in content]
    assert types == ["Scene Heading", "Action", "Character", "Dialogue"]
    assert content[0]["text"] == "INT. COFFEE SHOP - DAY"
    assert content[0]["number"] == "1"
    assert content[2]["text"] == "JOHN"

    tp_texts = [p["text"] for p in titlepage]
    assert "MY GREAT SCRIPT" in tp_texts
    assert "Written by Jane Doe" in tp_texts
