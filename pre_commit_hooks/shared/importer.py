"""Helper file to import gitlab yaml files"""
from __future__ import annotations
import os
import sys
from pathlib import Path
from dataclasses import dataclass
from git import Repo


import yaml

# reduce(lambda xy: xy[0][xy[1]], thing)
from lenses import lens


class Loader(yaml.SafeLoader):  # pylint: disable=too-many-ancestors
    pass


class Dumper(yaml.SafeDumper):
    pass


def recursive_lookup(lookup_key, dictionary):
    """Walk the dictionary and find a nested key"""
    if lookup_key in dictionary:
        return dictionary[lookup_key]
    for v in dictionary.values():
        if isinstance(v, dict):
            recurse = recursive_lookup(lookup_key, v)
            if recurse is not None:
                return recurse
    return None


@dataclass
class Reference:
    """Sets !reference instances in yaml files to this object when parsed"""

    data: list


def parse_out_references(
    previous_yaml: list, current_yaml: dict, current_dictionary: dict
):
    """Replace reference objects in a provided dictionary with the code they reference"""
    queue = [lens]  # Initialize a queue, this will be the path through the dict
    while len(queue) > 0:  # Creating loop to visit each node
        m = queue.pop(0)  # lens element
        element = m.get()(current_yaml)  # Lens value
        if isinstance(element, dict):
            next_keys = element.keys()
            for key in next_keys:
                # focus into the next element
                queue.append(m[key])
        if isinstance(element, list):
            # Can turn this into a separate func to unit test
            replace_data = []
            snapshotted_yaml = lens.get()(current_yaml)
            for list_element in range(len(element)):
                if isinstance(element[list_element], Reference):
                    replace, current_dictionary = find_reference(
                        element[list_element],
                        previous_yaml,
                        snapshotted_yaml,
                        current_dictionary,
                    )
                    replace_data.append((list_element, replace))
                    # replace the reference object with the value to sub
            new_data = []
            index = 0
            for replacement in replace_data:
                new_data = new_data + element[index : replacement[0]] + replacement[1]
                index = replacement[0] + 1
            new_data = new_data + element[index:]

            current_yaml = m.set(new_data)(current_yaml)

            # There may be more elements in the list now
            list_elements_after_sub = m.get()(current_yaml)
            for i in range(len(list_elements_after_sub)):
                # focus into the list in case anything is nested inside
                queue.append(m[i])
        if isinstance(element, str):
            continue
        if isinstance(element, Reference):
            # May not be hitting this path, as we don't wanna replace with a list one too deep.
            # Handled better when going through the list.
            # One last case to check would be to be if a value within a dict is reference
            # then inline sub with list

            replace, current_dictionary = find_reference(
                element, previous_yaml, lens.get()(current_yaml), current_dictionary
            )
            # replace the reference object with the value to sub
            # Nested 1 too far in. Want to add it to previous list
            current_yaml = m.set(replace)(current_yaml)
    return lens.get()(current_yaml), current_dictionary


def find_reference(
    reference: Reference,
    previous_yamls: list,
    current_yaml: dict,
    current_dictionary: dict,
):
    """Find the code the !reference object refers to"""
    if str(reference.data) in current_dictionary:
        return current_dictionary[str(reference.data)], current_dictionary
    lookup = recursive_lookup(reference.data[0], current_yaml)
    if lookup:
        # Look up the key in the job found
        wanted = recursive_lookup(reference.data[1], lookup)
        current_dictionary[str(reference.data)] = wanted
        return wanted, current_dictionary

    for previous_yaml in previous_yamls:
        lookup = recursive_lookup(reference.data[0], previous_yaml)
        if lookup:
            # Look up the key in the job found
            wanted = recursive_lookup(reference.data[1], lookup)
            current_dictionary[str(reference.data)] = wanted
            return wanted, current_dictionary
    return None


def constructor_reference(loader, node) -> Reference:
    """Extends the yaml constructor to parse !reference tags into a reference object"""
    return Reference(loader.construct_sequence(node))


Loader.add_constructor("!reference", constructor_reference)


def check_if_importable(file_path_str: str) -> bool:
    """Check if the file path exists and is of type yaml"""
    if "http" in file_path_str:
        return False
    if file_path_str[-5:] != ".yaml" and file_path_str[-4:] != ".yml":
        print(f"Warning: Tried to import a non YAML file: {file_path_str}")
        return False
    if "/templates/" in file_path_str:
        return False
    return True


def import_from_root_file(root_file: str) -> (list, bool):
    """Entry point to import all yaml files starting with the root file."""
    files_to_import = []
    import_queue = [root_file]
    ci_yaml = []
    reference_dict = {}
    ok = True
    while len(import_queue) > 0:
        yaml_to_import = {}
        filename_to_import = import_queue.pop(0)
        try:
            with open(filename_to_import) as stream:
                # TODO: parse in safety arg
                yaml_to_import = yaml.load(stream, Loader=Loader)
                stream.close()
        except Exception as ex:
            print(f"Error: could not import file {files_to_import}")
            print(ex)
            ok = False

        yaml_to_import, reference_dict = parse_out_references(
            [x[0] for x in ci_yaml], yaml_to_import, reference_dict
        )

        ci_yaml.append((yaml_to_import, filename_to_import))
        current_import_path = str(os.path.dirname(filename_to_import))

        new_imports = import_from_yaml(yaml_to_import)
        for importing in new_imports:
            if os.path.exists(importing):
                import_queue.append(importing)
            elif os.path.exists(current_import_path + os.sep + importing):
                import_queue.append(current_import_path + os.sep + importing)
            else:
                ok = False
                print(f"Could not find import for file: {importing}")
    return ci_yaml, ok


def import_from_yaml(yaml_data: dict) -> list:
    """Grabs the references to other files via import tags in a yaml dict."""
    to_import = []
    if "include" in yaml_data:
        if isinstance(yaml_data["include"], list):
            # import_spec = [[]] + rootYAML["include"]

            # to_import = reduce(parseImportElement, import_spec)
            for spec in yaml_data["include"]:
                # call parse on each element in the list
                to_import = parse_import_element(to_import, spec)
        elif isinstance(yaml_data["include"], str):
            if check_if_importable(yaml_data["include"]):
                to_import.append(yaml_data["include"])
    return to_import


def parse_import_element(existing_imports: list, element) -> list:
    """Helper function to only parse valid import definitions"""
    if isinstance(element, str) and check_if_importable(element):
        existing_imports.append(element)
    elif isinstance(element, list):
        for importable in element:
            if check_if_importable(importable):
                existing_imports.append(importable)
    elif isinstance(element, dict):
        # Importing from a template
        if "template" in element:
            # TODO: curl and parse from
            #  https://gitlab.com/gitlab-org/gitlab/-/tree/master/lib/gitlab/ci/templates
            return existing_imports
        if "remote" in element:
            # TODO: curl and parse from
            #  https://gitlab.com/gitlab-org/gitlab/-/tree/master/lib/gitlab/ci/templates
            return existing_imports
        # rules in importing the files in this dict
        if "rules" in element:
            # If the rules isn't a list, I haven't seen this before, so throw an error and lmk
            if not isinstance(element["rules"], list):
                print("unhandeled. code: 10299")
                sys.exit(1)
            passed_rules = True
            for rule in element["rules"]:
                if isinstance(rule, dict):
                    for rule_type, condition in rule.items():
                        rule_type = rule_type.lower()
                        # If it's an if statement, ignore. Evaluated at runtime
                        if rule_type == "if":
                            continue
                        # Unsure whether to check this at compile time.
                        if rule_type == "exists":
                            # If checking if a str exists and it does not,
                            # pass on the associated import
                            if isinstance(condition, str) and not check_if_importable(
                                condition
                            ):
                                passed_rules = False
                            # If the exists condition has multiple conditions,
                            # IE, checking multiple files
                            elif isinstance(condition, list):
                                for element2 in condition:
                                    if isinstance(
                                        element2, str
                                    ) and not check_if_importable(element2):
                                        passed_rules = False
                                    elif not isinstance(element2, str):
                                        print("Haven't seen this happen. code: 1838")
                                        sys.exit(1)
            if not passed_rules:
                return existing_imports
        if "local" in element and check_if_importable(element["local"]):
            existing_imports.append(element["local"])

    return existing_imports


def find_root_ci_file(root_file_name: str):
    """Finds the root CI file by looking at the base git repo path."""
    # If root file is not specified, look for default location
    # Get git root directory
    git_root = Repo(".", search_parent_directories=True).working_tree_dir
    # Store cwd to return after execution
    stored_cwd = os.getcwd()
    # set working directory to base of git repo
    os.chdir(str(git_root))

    file = str(Path(root_file_name))

    # Path to root file
    base_path = os.path.dirname(file)
    if base_path and len(base_path) > 1:
        # If specified file doesn't exist in git root:
        os.chdir(str(base_path))

    # Filename of root file without directories
    file = os.path.basename(file)

    # # Currently only check if .gitlab-ci.yml has changed
    # 	# cmd = "git diff-index --name-only --diff-filter M HEAD | grep '^.gitlab-ci.yml$'"
    # 	# ci_changed = os.system(cmd) == 0
    # 	# if not ci_changed:
    # 	# 	return True

    # Initial logic checks:
    if not os.path.exists(file):
        print(f"Root CI file {file} does not exist")
        print(f"debug: cwd is {str(os.getcwd())}")
        sys.exit(1)
    return file, stored_cwd
