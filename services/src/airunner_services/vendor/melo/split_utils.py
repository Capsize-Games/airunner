import re

from airunner.enums import AvailableLanguage


def split_sentence(
    text, min_len=10, language: AvailableLanguage = AvailableLanguage.EN
):
    if language in [
        AvailableLanguage.EN,
        AvailableLanguage.FR,
        AvailableLanguage.ES,
        AvailableLanguage.SP,
    ]:
        sentences = split_sentences_latin(text, min_len=min_len)
    else:
        sentences = split_sentences_zh(text, min_len=min_len)
    return sentences


def split_sentences_latin(text, min_len=10):
    text = re.sub("[。！？；]", ".", text)
    text = re.sub("[，]", ",", text)
    text = re.sub("[“”]", '"', text)
    text = re.sub("[‘’]", "'", text)
    text = re.sub(r"[\<\>\(\)\[\]\"\«\»]+", "", text)
    return [item.strip() for item in txtsplit(text, 256, 512) if item.strip()]


def split_sentences_zh(text, min_len=10):
    text = re.sub("[。！？；]", ".", text)
    text = re.sub("[，]", ",", text)
    # 将文本中的换行符、空格和制表符替换为空格
    text = re.sub("[\n\t ]+", " ", text)
    # 在标点符号后添加一个空格
    text = re.sub("([,.!?;])", r"\1 $#!", text)
    # 分隔句子并去除前后空格
    # sentences = [s.strip() for s in re.split('(。|！|？|；)', text)]
    sentences = [s.strip() for s in text.split("$#!")]
    if len(sentences[-1]) == 0:
        del sentences[-1]

    new_sentences = []
    new_sent = []
    count_len = 0
    for ind, sent in enumerate(sentences):
        new_sent.append(sent)
        count_len += len(sent)
        if count_len > min_len or ind == len(sentences) - 1:
            count_len = 0
            new_sentences.append(" ".join(new_sent))
            new_sent = []
    return merge_short_sentences_zh(new_sentences)


def merge_short_sentences_en(sens):
    """Avoid short sentences by merging them with the following sentence.

    Args:
        List[str]: list of input sentences.

    Returns:
        List[str]: list of output sentences.
    """
    sens_out = []
    for s in sens:
        # If the previous sentense is too short, merge them with
        # the current sentence.
        if len(sens_out) > 0 and len(sens_out[-1].split(" ")) <= 2:
            sens_out[-1] = sens_out[-1] + " " + s
        else:
            sens_out.append(s)
    try:
        if len(sens_out[-1].split(" ")) <= 2:
            sens_out[-2] = sens_out[-2] + " " + sens_out[-1]
            sens_out.pop(-1)
    except:
        pass
    return sens_out


def merge_short_sentences_zh(sens):
    # return sens
    """Avoid short sentences by merging them with the following sentence.

    Args:
        List[str]: list of input sentences.

    Returns:
        List[str]: list of output sentences.
    """
    sens_out = []
    for s in sens:
        # If the previous sentense is too short, merge them with
        # the current sentence.
        if len(sens_out) > 0 and len(sens_out[-1]) <= 2:
            sens_out[-1] = sens_out[-1] + " " + s
        else:
            sens_out.append(s)
    try:
        if len(sens_out[-1]) <= 2:
            sens_out[-2] = sens_out[-2] + " " + sens_out[-1]
            sens_out.pop(-1)
    except:
        pass
    return sens_out


def txtsplit(text, desired_length=100, max_length=200):
    """Split text it into chunks of a desired length trying to keep sentences intact."""
    text = re.sub(r"\n\n+", "\n", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r'[""]', '"', text)
    text = re.sub(r"([,.?!])", r"\1 ", text)
    text = re.sub(r"\s+", " ", text)

    rv = []
    in_quote = False
    current = ""
    split_pos = []
    pos = -1
    end_pos = len(text) - 1

    def seek(delta):
        nonlocal pos, in_quote, current
        is_neg = delta < 0
        for _ in range(abs(delta)):
            if is_neg:
                pos -= 1
                current = current[:-1]
            else:
                pos += 1
                current += text[pos]
            if text[pos] == '"':
                in_quote = not in_quote
        return text[pos]

    def peek(delta):
        p = pos + delta
        return text[p] if p < end_pos and p >= 0 else ""

    def commit():
        nonlocal rv, current, split_pos
        rv.append(current)
        current = ""
        split_pos = []

    while pos < end_pos:
        c = seek(1)
        if len(current) >= max_length:
            if len(split_pos) > 0 and len(current) > (desired_length / 2):
                d = pos - split_pos[-1]
                seek(-d)
            else:
                while (
                    c not in "!?.\n "
                    and pos > 0
                    and len(current) > desired_length
                ):
                    c = seek(-1)
            commit()
        elif not in_quote and (
            c in "!?\n" or (c in ".," and peek(1) in "\n ")
        ):
            while (
                pos < len(text) - 1
                and len(current) < max_length
                and peek(1) in "!?."
            ):
                c = seek(1)
            split_pos.append(pos)
            if len(current) >= desired_length:
                commit()
        elif in_quote and peek(1) == '"' and peek(2) in "\n ":
            seek(2)
            split_pos.append(pos)
    rv.append(current)
    rv = [s.strip() for s in rv]
    rv = [s for s in rv if len(s) > 0 and not re.match(r"^[\s\.,;:!?]*$", s)]
    return rv
