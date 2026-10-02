"""One presentation view of two explicitly different scoring interpretations."""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

AUDIT_DIR = "results/formal/ai_review_20261001"
PRESENTATION_DIR = "results/presentation_20261001"
CATEGORIES = ("requirements", "deadlines", "submission_information", "concepts")


def load_presentation(project: Path) -> dict:
    review = json.loads((project / AUDIT_DIR / "review_summary.json").read_text(encoding="utf-8"))
    experiment = json.loads((project / "results/formal/experiment_summary.json").read_text(encoding="utf-8"))
    assert not review["human_review_completed"]
    assert all(review["overall"][c]["reviewed"] == 40 for c in ("raw", "rag"))
    return {"review": review, "experiment": experiment,
            "method": "AI-assisted, unblinded, post-hoc review; not human-validated",
            "scope": "Strict completeness requires every frozen required fact. Missing detail is not always factual error."}


def build_charts(project: Path):
    data = load_presentation(project)
    review, experiment = data["review"], data["experiment"]
    dest = project / PRESENTATION_DIR
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "presentation_summary.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    def font(size, bold=False):
        return ImageFont.truetype(str(Path("C:/Windows/Fonts") / ("arialbd.ttf" if bold else "arial.ttf")), size)
    raw_color, rag_color, navy = "#c65a18", "#3368b0", "#17365d"
    im = Image.new("RGB", (1600, 1000), "white")
    d = ImageDraw.Draw(im)
    d.text((75, 45), "Strict completeness by category", font=font(44, True), fill=navy)
    d.text((75, 110), "AI-assisted post-hoc audit of the same saved outputs; not human-validated", font=font(25), fill="#444444")
    d.text((75, 152), "Every frozen required fact must be covered. Some requirements exceed the question wording.", font=font(23), fill="#444444")
    left, right, top, bottom = 130, 1500, 240, 760
    for value in range(0, 11, 2):
        y = bottom - value / 10 * (bottom-top)
        d.line((left, y, right, y), fill="#d9d9d9", width=2)
        d.text((78, y-14), str(value), font=font(23), fill="#555555")
    for i, (category, label) in enumerate(zip(CATEGORIES, ("Requirements", "Deadlines", "Submission info", "Concepts"))):
        centre = left + (right-left) / 4 * (i+.5)
        for condition, offset, color in (("raw",-67,raw_color),("rag",67,rag_color)):
            n = review["by_category"][condition][category]["strict_completeness_score"]
            x, y = centre+offset-48, bottom-n/10*(bottom-top)
            if n:
                d.rectangle((x,y,x+96,bottom),fill=color)
            d.text((x+5,y-34),f"{n}/10",font=font(25,True),fill=color)
        box=d.textbbox((0,0),label,font=font(24,True))
        d.text((centre-(box[2]-box[0])/2,bottom+24),label,font=font(24,True),fill=navy)
    r, g = review["overall"]["raw"], review["overall"]["rag"]
    d.text((75, 837), f"Raw {r['strict_completeness_score']}/40", font=font(29,True),fill=raw_color)
    d.text((365, 837), f"RAG {g['strict_completeness_score']}/40", font=font(29,True),fill=rag_color)
    d.text((75, 895), f"Historical provisional answer scores: Raw {r['original_answer_score']}/40; RAG {g['original_answer_score']}/40.",font=font(24),fill="#444444")
    d.text((75, 936), "Different scoring interpretations, not new model runs or a retrieval-only causal estimate.",font=font(23),fill="#444444")
    im.save(dest/"strict_completeness_by_category.png")
    im = Image.new("RGB", (1600, 1000), "white")
    d = ImageDraw.Draw(im)
    d.text((75,45),"Scoring and generation API measurements",font=font(42,True),fill=navy)
    d.text((75,110),data["method"],font=font(25),fill="#444444")
    er, eg = experiment["conditions"]["raw"],experiment["conditions"]["rag"]
    rows=[
        ("Historical provisional answer score",f"{r['original_answer_score']}/40",f"{g['original_answer_score']}/40"),
        ("Post-hoc strict completeness",f"{r['strict_completeness_score']}/40",f"{g['strict_completeness_score']}/40"),
        ("Page-citation support in the audit",f"{r['page_citation_support_score']}/40",f"{g['page_citation_support_score']}/40"),
        ("Strict complete AND page-supported",f"{r['strict_complete_and_cited']}/40",f"{g['strict_complete_and_cited']}/40"),
        ("API cost per 1,000 questions",f"${er['projected_cost_per_1000_questions_usd']:.4f}",f"${eg['projected_cost_per_1000_questions_usd']:.4f}"),
        ("Mean API request time",f"{er['average_latency_seconds']:.3f} s",f"{eg['average_latency_seconds']:.3f} s"),
        ("Logged abstained flag",f"{r['model_abstained_flags']}/40",f"{g['model_abstained_flags']}/40"),
    ]
    d.text((75,187),"Measure",font=font(27,True),fill=navy)
    d.text((1010,187),"Raw",font=font(27,True),fill=raw_color)
    d.text((1270,187),"RAG",font=font(27,True),fill=rag_color)
    for i,(label,a,b) in enumerate(rows):
        y=245+i*76
        if i%2==0:d.rectangle((65,y-10,1510,y+57),fill="#f3f5f8")
        d.text((80,y),label,font=font(26),fill=navy)
        d.text((1000,y),a,font=font(29,True),fill=raw_color)
        d.text((1260,y),b,font=font(29,True),fill=rag_color)
    d.text((75,811),"API time excludes retrieval and browser time. No speed advantage is established.",font=font(24),fill="#444444")
    d.text((75,852),"Abstained flags do not always match prose. Costs exclude embeddings, hosting and review.",font=font(24),fill="#444444")
    d.text((75,908),f"Model: {experiment['model']}   |   Recorded prices: {experiment['price_checked_on']}",font=font(23),fill="#444444")
    im.save(dest/"scoring_cost_api_latency.png")
    print(dest)


if __name__ == "__main__":
    build_charts(Path(__file__).resolve().parents[1])
