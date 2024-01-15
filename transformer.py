from pygments.lexers import get_lexer_by_name
from pygments.token import Name, Keyword, Text, Operator, Punctuation, Comment, Literal
from pygments import lex
import argparse
import crc16
import copy
import os
import re

snake_marks = "_?!:"
builtins = [
    "divmod", "~divmod", "moddiv", "~moddiv", "muldiv", "muldivc", "muldivr", "muldivmod",
    "true", "false", "null", "nil", "Nil", "throw", "at",
    "touch", "~touch", "touch2", "~touch2", "~dump", "~strdump",
    "run_method0", "run_method1", "run_method2", "run_method3", "->"
]
camel_replace_map = {
    "recv_internal": "receiveInternalMessage",
    "recv_external": "receiveExternalMessage",
    "slice_empty?": "isSliceEmpty",
    "slice_data_empty?": "isSliceDataEmpty",
    "slice_refs_empty?": "isSliceRefsEmpty",
    "dict_empty?": "isDictEmpty",
    "cell_null?": "isCellNull",
    "tryComputeDataSize": "tryComputeDataSize",
    "trySliceComputeDataSize": "trySliceComputeDataSize",
    "idict_get_ref?": "tryIdictGetRef",
    "udict_get_ref?": "tryUdictGetRef",
    "idict_delete?": "tryIdictDelete",
    "udict_delete?": "tryUdictDelete",
    "idict_get?": "tryIdictGet",
    "udict_get?": "tryUdictGet",
    "idict_delete_get?": "tryIdictDeleteGet",
    "udict_delete_get?": "tryUdictDeleteGet",
    "~idict_delete_get?": "~tryIdictDeleteGet",
    "~udict_delete_get?": "~tryUdictDeleteGet",
    "udict_add?": "tryUdictAdd",
    "udict_replace?": "tryUdictReplace",
    "idict_add?": "tryIdictAdd",
    "idict_replace?": "tryIdictReplace",
    "udict_add_builder?": "tryUdictAddBuilder",
    "udict_replace_builder?": "tryUdictReplaceBuilder",
    "idict_add_builder?": "tryIdictAddBuilder",
    "idict_replace_builder?": "tryIdictReplaceBuilder",
    "udict_get_min?": "tryUdictGetMin",
    "udict_get_max?": "tryUdictGetMax",
    "udict_get_min_ref?": "tryUdictGetMinRef",
    "udict_get_max_ref?": "tryUdictGetMaxRef",
    "idict_get_min?": "tryIdictGetMin",
    "idict_get_max?": "tryIdictGetMax",
    "idict_get_min_ref?": "tryIdictGetMinRef",
    "idict_get_max_ref?": "tryIdictGetMaxRef",
    "udict_get_next?": "tryUdictGetNext",
    "udict_get_nexteq?": "tryUdictGetNexteq",
    "udict_get_prev?": "tryUdictGetPrev",
    "udict_get_preveq?": "tryUdictGetPreveq",
    "idict_get_next?": "tryIdictGetNext",
    "idict_get_nexteq?": "tryIdictGetNexteq",
    "idict_get_prev?": "tryIdictGetPrev",
    "idict_get_preveq?": "tryIdictGetPreveq",
    "pfxdict_get?": "tryPfxdictGet",
    "pfxdict_set?": "tryPfxdictSet",
    "pfxdict_delete?": "tryPfxdictDelete",

}

snake_replace_map = {value: key for key, value in camel_replace_map.items()}


def is_snake_case(input_str: str) -> bool:
    return all(char.islower() or char.isdigit() or char in snake_marks for char in input_str)


def is_camel_case(input_str: str) -> bool:
    return input_str[0].islower() and any(char.isupper() for char in input_str)


def snake_to_camel(input_str: str) -> str:
    words = input_str.split("_")
    camel_case_words = [words[0].lower()] + [word.capitalize() for word in words[1:]]
    camel_case_str = "".join(camel_case_words)

    return camel_case_str


def camel_to_snake(input_str: str) -> str:
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", input_str).lower()


def transform_question_mark(input_str: str) -> str:
    if not input_str.endswith("?"):
        return input_str
    if "_" in input_str:
        return input_str[:-1]
    else:
        transformed_str = "is_" + input_str[:-1]
        return transformed_str


def transform_exclamation_mark(input_str: str) -> str:
    if not input_str.endswith("!"):
        return input_str
    transformed_str = "force_" + input_str[:-1]

    return transformed_str


def transform_apostrophe(input_str: str) -> str:
    if not input_str.endswith("'"):
        return input_str
    transformed_str = "modified_" + input_str[:-1]

    return transformed_str


def transform_is_word(input_str: str) -> str:
    if not (input_str.startswith("is") and len(re.findall(r'[a-z][A-Z]', input_str)) == 1):
        return input_str
    transformed_str = input_str[2:] + "?"

    return transformed_str


def transform_force_word(input_str: str) -> str:
    if not (input_str.startswith("force") and input_str[5].isupper()):
        return input_str
    transformed_str = input_str[5:] + "!"

    return transformed_str


def transform_modified_word(input_str: str) -> str:
    if not (input_str.startswith("modified") and input_str[8].isupper()):
        return input_str
    transformed_str = input_str[8:] + "'"

    return transformed_str


def transform_string_to_camel_case(input_str: str) -> str:
    if not is_snake_case(input_str) or input_str in builtins:
        return input_str
    if input_str in camel_replace_map.keys():
        return camel_replace_map.get(input_str, input_str)

    question_result = transform_question_mark(input_str)
    exclamation_result = transform_exclamation_mark(question_result)
    apostrophe_result = transform_apostrophe(exclamation_result)
    camel_result = snake_to_camel(apostrophe_result)
    return camel_result


def transform_string_to_snake_case(input_str: str) -> str:
    if not is_camel_case(input_str) or input_str in builtins:
        return input_str
    if input_str in snake_replace_map.keys():
        return snake_replace_map.get(input_str, input_str)

    is_word_result = transform_is_word(input_str)
    force_word_result = transform_force_word(is_word_result)
    modified_word_result = transform_modified_word(force_word_result)
    snake_result = camel_to_snake(modified_word_result)
    return snake_result


def transform_string(input_str: str, mode: int) -> str:
    if mode == 1:
        return transform_string_to_camel_case(input_str)
    elif mode == 2:
        return transform_string_to_snake_case(input_str)
    return input_str


def insert_method_id(matchobj: re.Match) -> str:
    func_name = matchobj.group(1)
    crc = crc16.crc16xmodem(bytes(func_name, "UTF-8"))
    params = matchobj.group(2)
    method_id = matchobj.group(3) if matchobj.group(3) else f"{(crc & 0xffff) | 0x10000}"
    return f"{func_name}{params} method_id({method_id}) {{"


def transform(input_file_path: str, output_dir: str, mode: int = 1):
    input_dir = os.path.dirname(input_file_path)
    input_filename = os.path.basename(input_file_path)
    output_path = os.path.join(input_dir, output_dir)

    lexer = get_lexer_by_name("func")

    include_files = [input_filename]

    while len(include_files):
        work_file = include_files.pop(0)
        result_path = os.path.join(output_path, work_file)
        os.makedirs(os.path.dirname(result_path), exist_ok=True)

        with open(work_file, "r") as file:
            code = file.read()

        regex = r"([\w\?]+)\s*(\(.*?\))\s*method_id(?:\s*\(\s*(\d+)\s*\))?\s{"
        code = re.sub(regex, insert_method_id, code)

        tokens = list(lex(code, lexer))

        temp_tokens = copy.deepcopy(tokens)
        into_include = False

        for idx, token in enumerate(temp_tokens):
            if token[0] in [Keyword, Name.Variable, Name.Function]:
                temp_tokens[idx] = (token[0], transform_string(token[1], mode))
            if into_include:
                if token[0] is Literal.String and (token[1][1:-1].endswith(".func") or token[1][1:-1].endswith(".fc")):
                    include_file = token[1][1:-1]
                    if include_file not in include_files:
                        include_files.append(include_file)
                elif token == (Text, ';'):
                    into_include = False
            if token == (Keyword, '#include'):
                into_include = True

        result_string = "".join(token[1] for token in temp_tokens)
        with open(result_path, "w") as file:
            file.write(result_string)


def main():
    parser = argparse.ArgumentParser(
        prog="transformer",
        description="FunC code snakeToCamel and camel_to_snake transformer",
    )

    parser.add_argument("-o", "--output", dest="output", default="result", help="output dir name")
    parser.add_argument("-m", "--mode", dest="mode", default=1, type=int, choices=[1, 2],
                        help="transform mode (1 - snakeToCamel; 2 - camel_to_snake)")
    parser.add_argument("filename")

    args = parser.parse_args()

    transform(args.filename, args.output, args.mode)


if __name__ == "__main__":
    main()
