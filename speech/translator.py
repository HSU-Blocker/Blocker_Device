from googletrans import Translator

class TranslatorModule:
    def __init__(self):
        self.translator = Translator()

    def translate(self, text, dest="ko"):
        try:
            result = self.translator.translate(text, dest=dest)
            return result.text
        except Exception as e:
            print(f"[WARN] 번역 실패: {e}")
            return text
