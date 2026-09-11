"""Small retrieval guides, never source evidence. Every suggested file is verified live.

Automatic public queries use this finite vocabulary, not text copied from a private
document. Unrecognized concepts require an explicit user-supplied search term.
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Guide:
    concept: str
    pattern: str
    terms: tuple[str, ...]
    repositories: tuple[str, ...]
    paths: tuple[str, ...]


GUIDES = (
    Guide("梯度与反向传播", r"gradient|backprop|梯度|反向传播", ("gradient", "backward"),
          ("karpathy/micrograd",), ("micrograd/engine.py",)),
    Guide("注意力机制", r"attention|transformer|注意力", ("attention", "forward"),
          ("karpathy/minGPT",), ("mingpt/model.py",)),
    Guide("分类与预测", r"logistic|classification|逻辑回归|分类器", ("logistic", "predict", "fit"),
          ("scikit-learn/scikit-learn",),
          ("examples/linear_model/plot_logistic_multinomial.py", "examples/linear_model/plot_iris_logistic.py",
           "sklearn/linear_model/_logistic.py")),
    Guide("输入、目标与预测", r"\blabels?\b|\btarget\b|\bpredict\w*\b|\binput\s*x\b|"
          r"regression|supervised|标签|预测|回归|监督学习",
          ("linear regression", "predict", "fit", "target"), ("scikit-learn/scikit-learn",),
          ("examples/linear_model/plot_ols_ridge.py", "examples/linear_model/plot_ols.py",
           "sklearn/linear_model/_base.py")),
    Guide("聚类", r"k.?means|clustering|聚类", ("kmeans", "cluster"),
          ("scikit-learn/scikit-learn",),
          ("examples/cluster/plot_kmeans_digits.py", "sklearn/cluster/_kmeans.py")),
    Guide("决策树", r"decision.?tree|决策树", ("decision tree", "predict"),
          ("scikit-learn/scikit-learn",),
          ("examples/tree/plot_iris_dtc.py", "sklearn/tree/_classes.py")),
    Guide("数据集划分", r"train.?test.?split|训练集|测试集|数据集划分", ("train_test_split",),
          ("scikit-learn/scikit-learn",), ("sklearn/model_selection/_split.py",)),
    Guide("依赖注入", r"dependenc\w*\s*inject|依赖注入|\bDepends\b", ("dependency injection", "Depends"),
          ("fastapi/fastapi",), ("docs_src/dependencies/tutorial001.py",)),
    Guide("路由与请求", r"\bfastapi\b|\brout\w*\b|路由", ("routing", "request"),
          ("fastapi/fastapi",), ("fastapi/routing.py",)),
    Guide("张量与自动求导", r"\bautograd\b|\btensor\b|张量|自动求导", ("autograd", "backward"),
          ("karpathy/micrograd",), ("micrograd/engine.py",)),
)


def guide_for(text):
    return next((guide for guide in GUIDES if re.search(guide.pattern, text, re.I)), None)


def guide_for_terms(terms):
    normalized = {term.casefold().strip() for term in terms}
    # A full guide signature is more specific than a shared word such as predict.
    return next((guide for guide in GUIDES if {term.casefold() for term in guide.terms} <= normalized), None)


def public_terms(terms):
    allowed = {term.casefold() for guide in GUIDES for term in guide.terms}
    return list(dict.fromkeys(term.casefold().strip() for term in terms
                             if term.casefold().strip() in allowed))
