import os
import re
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def extract_trait_blocks(content):
    traits = []
    pattern = re.compile(r'(trait_[\w\d_]+)\s*=')
    pos = 0

    while match := pattern.search(content, pos):
        trait_name = match.group(1)
        brace_start = content.find('{', match.end())
        if brace_start == -1:
            break

        brace_count = 1
        i = brace_start + 1
        while i < len(content) and brace_count > 0:
            if content[i] == '{':
                brace_count += 1
            elif content[i] == '}':
                brace_count -= 1
            i += 1

        trait_block = content[match.start():i]
        traits.append((trait_name, trait_block.strip()))
        pos = i

    return traits


def analyze_modifier(modifier_block):
    tags = []
    has_positive_job_bonus = False

    for line in modifier_block.splitlines():
        line = line.strip()
        if not line or '=' not in line:
            continue

        key, value = map(str.strip, line.split('=', 1))
        try:
            value = float(value)
        except ValueError:
            logging.warn(f"Strange value found {value}")
            continue

        if 'jobs_bonus' in key or 'cat_bonus' in key or 'planet_jobs' in key:
            if value > 0:
                has_positive_job_bonus = True
        if 'pop_environment_tolerance' in key:
            if value > 0:
                tags.append('habitability')
        if 'leader' in key:
            if value > 0:
                tags.append('leader')
        if 'army' in key:
            tags.append('army')
        if 'immigration' in key:
            tags.append('migration')
        if 'growth_mult' in key:
            tags.append('pop_growth')
        if 'livestock' in key:
            tags.append('livestock')
        if 'housing_usage' in key:
            tags.append('housing')
        if 'upkeep' in key:
            tags.append('upkeep')

    if has_positive_job_bonus:
        tags.append('pop_output')

    return list(set(tags))


def parse_traits(file_path, output_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    trait_blocks = extract_trait_blocks(content)

    processed_traits = []
    skipped_count = 0
    added_count = 0

    for trait_name, trait_text in trait_blocks:
        tags = []

        logging.info(f"working on traint {trait_name}")

        cost_match = re.search(r'cost\s*=\s*([-+]?\d+)', trait_text)
        if not cost_match:
            logging.info(f"{trait_name} — skipped: no 'cost'")
            skipped_count += 1
            continue
        cost = int(cost_match.group(1))
        if cost < 0:
            tags.append("negative")
        else:
            tags.append("positive")
        category = extract_value(r'category\s*=\s*(\w+)', trait_text)
        if 'cyborg' in category:
            tags.append("cybernetic")
        isAdvanced = extract_value(r'advanced_trait\s*=\s*(\w+)', trait_text)

        # archetypes
        archetypes_match = re.search(r'allowed_archetypes\s*=\s*\{(.*?)\}', trait_text, re.DOTALL)
        if archetypes_match:
            archetypes = archetypes_match.group(1).split()
            if "MACHINE" in archetypes or "ROBOT" in archetypes:
                tags.append("machine")
            if "BIOLOGICAL" in archetypes:
                tags.append("organic")
                if isAdvanced is 'yes':
                    tags.append("genetic_ascension")
            if "LITHOID" in archetypes and "BIOLOGICAL" not in archetypes:
                tags.append("organic")
                tags.append("lithoid")
                tags.append("species")
                if isAdvanced:
                    tags.append("genetic_ascension")
            if "PRESAPIENT" in archetypes:
                tags.append("presapient")
        else:
            logging.warn(f"{trait_name} — skipped: no 'allowed_archetypes'")
            skipped_count += 1
            processed_traits.append(trait_text)
            continue

        modifier_match = re.search(r'modifier\s*=\s*\{(.*?)\}', trait_text, re.DOTALL)
        if modifier_match:
            modifier_block = modifier_match.group(1)
            modifier_tags = analyze_modifier(modifier_block)
            tags.extend(tag for tag in modifier_tags if tag not in tags)

        insert_pos = trait_text.rfind('}')
        trait_with_tags = (
                trait_text[:insert_pos].rstrip() +
                '\n\ttags = {\n' +
                ''.join(f'\t\t"{tag}"\n' for tag in tags) +
                '\t}\n' +
                trait_text[insert_pos:]
        )

        processed_traits.append(trait_with_tags)
        added_count += 1
        logging.info(f"{trait_name} — added tags: {tags}")

    with open(output_path, 'w', encoding='utf-8') as output_file:
        output_file.write("\n\n".join(processed_traits))

    logging.info(f"\nDone.\nAdded: {added_count}\nSkipped: {skipped_count}")


def extract_value(pattern, text):
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ''


if __name__ == '__main__':
    path = ""
    txt_files = [f for f in os.listdir(path) if f.endswith(".txt")]
    for trait_file in txt_files:
        full_path = os.path.join(path, trait_file)
        logging.info(f"Work on {trait_file}")
        parse_traits(full_path, trait_file)
