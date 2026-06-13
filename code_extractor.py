def chapter_code_extractor(chapters):
    codes = []

    for chapter in chapters:
        code = ''
        lines = chapter.split('\n')

        for index, line in enumerate(lines):
            words = line.split()

            if len(words) > index:
                code += str(len(words[index]))
            else:
                code += '0'

        codes.append(code)

    return codes


chapter1 = """Python is amazing
Loops make coding easier
Functions organize logic"""

chapter2 = """Books contain knowledge
Practice builds skill
Consistency brings success"""

print(chapter_code_extractor([chapter1, chapter2]))