import re
from typing import List, Tuple, Optional
from songstring_parser.steps.brackets.models import Harvested
from songstring_parser.steps.brackets.models import _Span, ParseResult
from songstring_parser.conf import ParserConfig
from songstring_parser.steps.brackets.helpers import is_effectively_empty
from songstring_parser.steps.brackets.classifiers import FeatClassifier, LiveClassifier, RemixClassifier, NoiseClassifier, UnknownClassifier

class BracketParser:
    def __init__(self, cfg: ParserConfig = ParserConfig):
        
        self.cfg = ParserConfig()
        self.classifiers = [
            FeatClassifier(),
            LiveClassifier(),
            RemixClassifier(),
            NoiseClassifier(),
            UnknownClassifier()
        ]

        return

    def _find_spans_nested(self, s: str, pairs: List[Tuple[str, str]]) -> List[_Span]:
        openers = {l: r for (l, r) in pairs}
        closers = {r: l for (l, r) in pairs}
        stack: List[Tuple[str, int]] = []
        spans: List[_Span] = []
        for i, ch in enumerate(s):
            if ch in openers:
                stack.append((ch, i))
            elif ch in closers:
                if stack and stack[-1][0] == closers[ch]:
                    lch, pos = stack.pop()
                    depth = len(stack) + 1
                    spans.append(_Span(start=pos, end=i + 1, l=lch, r=ch, depth=depth))

        return spans

    def resolve(self, info: List[Harvested]) -> ParseResult:
        pr = ParseResult()

        for el in info:
            print(el)

        return pr




    def harvest_brackets(self, text: str = None):

        patterns = None

        # spans
        spans = self._find_spans_nested(s=text, pairs=self.cfg.bracket_pairs)
        ordered_spans = sorted(range(len(spans)), key=lambda i: (-spans[i].depth, spans[i].start))        

        # mask of what is still "visible" in the working string
        alive = [True] * len(text)

        # extract info from ALL SPANS
        info: List[Harvested] = []
        for idx in ordered_spans:
            sp = spans[idx]
            # get span text
            inner_chars = [
                text[i] for i in range(sp.start + 1, sp.end - 1)
                if 0 <= i < len(alive) and alive[i]
            ]
            inner_text = re.sub(r"\s{2,}", " ", "".join(inner_chars)).strip()  
            # ignore empty spans and remove them
            if is_effectively_empty(inner_text):
                for i in range(sp.start, sp.end):
                    if 0 <= i < len(alive):
                        alive[i] = False
                continue  
            # classify
            h = Optional[Harvested]
            for clf in self.classifiers:
                h = clf.classify(inner_text)
                if h: break
            # set data
            h.raw = sp.l + (inner_text if inner_text else "") + sp.r
            h.text = inner_text
            h.span = sp
            info.append(h)  
            # remove this span for parents
            for i in range(sp.start, sp.end):
                alive[i] = False     
            # clean text
            cleaned = "".join(ch for i, ch in enumerate(text) if alive[i])
            cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()      

        return cleaned, info
    

    def parse(self, text: str = None) -> ParseResult:

        cleaned_text, info = self.harvest_brackets(text)

        pr = self.resolve(info)

        return pr
    

def main():
    bp = BracketParser()

    r = bp.parse("Hallo ik ben barry (Extended Mix), {jemoedaaa}, [[feat dikzak]]")



if __name__ == '__main__':

    main()
