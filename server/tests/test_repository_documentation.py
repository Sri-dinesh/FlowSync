"""Maintained Markdown links must resolve to actual sections, not code examples."""
from scripts.check_repository import check_links


def test_missing_same_document_section_is_reported(tmp_path):
    document = tmp_path/"CONTENT.md"
    document.write_text("# Reference\n\n[Absent](#missing-section)\n")
    issues,_,_ = check_links(tmp_path,[document])
    assert any("missing local anchor" in issue for issue in issues)


def test_cross_document_section_is_checked(tmp_path):
    document = tmp_path/"README.md"
    target = tmp_path/"CONTENT.md"
    document.write_text("[Valid](CONTENT.md#21-observation-contract)\n[Stale](CONTENT.md#old-name)\n")
    target.write_text("## 2.1 Observation contract\n")
    issues,_,_ = check_links(tmp_path,[document,target])
    assert len(issues) == 1 and "old-name" in issues[0]


def test_explicit_and_duplicate_heading_anchors_resolve(tmp_path):
    document = tmp_path/"CONTENT.md"
    document.write_text('<a id="top"></a>\n# Reference\n## Notes\n## Notes\n'
        '[Top](#top) [First](#notes) [Second](#notes-1)\n')
    assert not check_links(tmp_path,[document])[0]


def test_fenced_examples_do_not_define_sections_or_create_file_links(tmp_path):
    document = tmp_path/"CONTENT.md"
    document.write_text('# Reference\n```bash\n# Not a heading\n[Example](missing-file.md)\n```\n'
        '[Absent](#not-a-heading)\n')
    issues,_,_ = check_links(tmp_path,[document])
    assert len(issues) == 1 and "not-a-heading" in issues[0]


def test_frozen_records_are_not_rewritten_by_current_link_checks(tmp_path):
    record = tmp_path/"research/docs/results/historical.md"
    record.parent.mkdir(parents=True)
    record.write_text('[Old path](removed-in-a-later-version.md#old-section)\n')
    before = record.read_bytes()
    assert not check_links(tmp_path,[record])[0]
    assert record.read_bytes() == before
