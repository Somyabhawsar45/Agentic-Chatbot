from src.langgraphagenticai.rag import pdf_rag_utils


def test_chunks_keep_page_numbers_and_skip_empty_pages():
    pages = ["", "Intro text on page two.", "Results: revenue grew 20%."]
    texts, metadatas = pdf_rag_utils.chunk_pages(pages, source="report.pdf")
    assert texts == ["Intro text on page two.", "Results: revenue grew 20%."]
    assert [m["page"] for m in metadatas] == [2, 3]
    assert all(m["source"] == "report.pdf" for m in metadatas)


def test_long_page_is_split_but_keeps_its_page():
    texts, metadatas = pdf_rag_utils.chunk_pages(["word " * 600], source="x.pdf")
    assert len(texts) > 1
    assert {m["page"] for m in metadatas} == {1}


def test_format_passages_labels_pages():
    block = pdf_rag_utils.format_passages([
        {"text": "alpha", "page": 4, "source": "a.pdf"},
        {"text": "beta", "page": None, "source": None},
    ])
    assert "[Passage 1, page 4]" in block
    assert "[Passage 2]" in block


def test_no_index_means_no_results():
    assert not pdf_rag_utils.has_index(None)
    assert not pdf_rag_utils.has_index(12345)
    assert pdf_rag_utils.retrieve(12345, "anything") == []
