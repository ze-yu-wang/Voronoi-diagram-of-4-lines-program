import yaml, os, re
from itertools import combinations_with_replacement, product, combinations, chain
import networkx as nx

class Branch:
    def __init__(self, name, label=None):
        self.name = name
        self.label = None  

        if label is not None:
            self.set_label(label)  
            
        '''A label is either an odd integer or an even integer followed by n or f, e.g. "1" or "2f"
        The number in the label is the number of vertices on that branch, if it is even, then it must
        be followed by 'n' or 'f' indicating the two unbounded parts of the branch belonging to 
        NVD or FVD respectively'''

    def set_label(self, label):
        self.label = label



class Trisector:
    def __init__(self, branches=None):
        # branches are stored in a dict {"M": Branch(...), "A": ..., "B": ..., "C": ...}
        default_names = ["M", "A", "B", "C"]
        self.branches = {}

        for name in default_names:
            self.branches[name] = branches.get(name) if branches and name in branches else Branch(name)

    def __getitem__(self, key):
        return self.branches[key]

    def __str__(self):
        return "\n".join(f"{name}: label={branch.label}" for name, branch in self.branches.items())


class TrisectorView:
# This class represent a trisector that is projected to a bisector, such that the U branch is fixed
    def __init__(self, trisector, U_name):
        if U_name not in ("A", "B", "C"):
            raise ValueError("U_name must be one of 'A', 'B', or 'C'")

        self.trisector = trisector 
        self.U_name = U_name

        self.M = trisector["M"]
        self.M_label = self.M.label

        self.U = trisector[U_name]
        self.U_label = self.U.label

        # L branches are the two not equal to U_name
        self.L_names = [name for name in ("A", "B", "C") if name != U_name]
        self.L = [trisector[name] for name in self.L_names]
        self.L_labels = [branch.label for branch in self.L]

    def __str__(self):
        lines = [
            f"TrisectorView (U = {self.U_name})",
            f"  M: label={self.M_label}",
            f"  U ({self.U_name}): label={self.U_label}",
            f"  L ({', '.join(self.L_names)}): labels={self.L_labels}"
        ]
        return "\n".join(lines)

class GenericTrisector:
    def __init__(self, label_M, label_U, label_L):
        '''
        label_L: a list of exactly two labels (duplicates allowed, order preserved), because we do not
        distinguish the two L branches
        '''
        if not isinstance(label_L, (list, tuple)) or len(label_L) != 2:
            raise ValueError("label_L must be a list of exactly two labels.")

        self.label_M = label_M
        self.label_U = label_U
        self.label_L = label_L

    def __str__(self):
        return (f"GenericTrisector:\n"
                f"  M: {self.label_M}\n"
                f"  U: {self.label_U}\n"
                f"  L: {self.label_L}")


class Config:
    def __init__(self, blue, red, name=None, num_nvd_faces=None):
        self.blue = blue
        self.red = red
        self.name = name  
        self.num_nvd_faces = num_nvd_faces

    def __str__(self):
        header = f"Config: {self.name}" if self.name else "Config:"
        return (
            f"{header}\n"
            f"--- Blue ---\n{self.blue}\n"
            f"--- Red ----\n{self.red}\n"
            f"--- Faces --\nnum_nvd_faces = {self.num_nvd_faces}"
        )
    
    def summary(self):
        return f"{self.name}" if self.name else "Unnamed Config"



def trisector_from_generic(generic):
    '''
    Create a new Trisector instance from a GenericTrisector.
    Assumes:
        - M gets label_M
        - U is assigned to branch A
        - L is assigned to branches B and C (unordered)

    Returns:
        A fully initialized Trisector.
    '''
    branches = {
        "M": Branch("M", generic.label_M),
        "A": Branch("A", generic.label_U),
    }

    branches["B"] = Branch("B", generic.label_L[0])
    branches["C"] = Branch("C", generic.label_L[1])

    return Trisector(branches)

def matches_view(generic, view):
    '''
    Compare a GenericTrisector with a TrisectorView.
    Returns True if their M, U, and L labels match.
    '''
    return (
        generic.label_M == view.M_label and
        generic.label_U == view.U_label and
        set(generic.label_L) == set(view.L_labels)
    )


''' The third digit in a configuration name represent the choice of the middle branch of the red trisector. If it is 1 or 2, then the red trisector's middle branch is horizontal, in which case red and blue trisectors are not parallel to each other, we use -1 to represent. If it is 3 or 4, then the middle branch is vertical, and the two trisectors are parallel to each other, we use +1 to represent. '''

def extract_third_digit(config_name):
    match = re.match(r"Config(\d+)", config_name)
    if match:
        digits = match.group(1)
        if len(digits) >= 3:
            if int(digits[2])<=2:
                return -1
            elif int(digits[2])<=4:
                return 1
    return None

''' Calculate the number of induced vertices in the map of unbounded features of the NVD for a trisector. If a branch has odd number of vertices, then it induces 1 such vertex. If it has even number of vertices, then it induces either 0 or 2 such vertices, which is indicated by the label of 'n' or 'f' after the digit. '''

def unbounded_generic_trisector(gt):
    def score_label(label):
        label = str(label).strip()
        if label.isdigit():
            return 1
        elif label.endswith("n"):
            return 2
        elif label.endswith("f"):
            return 0
        else:
            raise ValueError(f"Invalid label format: {label}")

    total = score_label(gt.label_M) + score_label(gt.label_U)
    for label in gt.label_L:
        total += score_label(label)

    return total

''' The following function checks whether a given configuration is indeed an (i, j) bisector. It is not necessary for the main search algorithm, just a helper to make sure that the imported configurations are as intended. '''

def check_config_unbounded(configs, expected_score_1, expected_score_2):
    any_invalid = False

    print(f"Checking the unbounded part of the trisectors in the configuration ......")

    for config in configs:
        score_blue = unbounded_generic_trisector(config.blue)
        score_red = unbounded_generic_trisector(config.red)

        if (score_blue == expected_score_1 and score_red == expected_score_2) or (score_blue == expected_score_2 and score_red == expected_score_1):
            continue
        else:
            any_invalid = True

    if not any_invalid:
        print(f"Test passed.")


''' Get the total number of vertices on a trisector. '''
def vertices_generic_trisector(gt):
    def extract_number(label):
        if label.isdigit():
            return int(label)
        elif label[-1] in ("n", "f") and label[:-1].isdigit():
            return int(label[:-1])
        else:
            raise ValueError(f"Invalid label format: {label}")

    total = extract_number(gt.label_M) + extract_number(gt.label_U)
    for label in gt.label_L:
        total += extract_number(label)

    return total

''' This function checks whether the total number of vertices on the red and blue trisectors in a configuration match the intended number of vertices. It is not necessary for the main search algorithm, but serves as a helper to check whether the configurations are intended. '''

def check_config_vertices(configs, expected_num_vert):
    any_invalid = False

    print(f"Checking the vertices of the trisectors in the configuration ......")

    for config in configs:
        score_blue = vertices_generic_trisector(config.blue)
        score_red = vertices_generic_trisector(config.red)

        if (score_blue == expected_num_vert) and (score_red == expected_num_vert):
            continue
        else:
            any_invalid = True

    if not any_invalid:
        print(f"Test passed.")  # Returns True if all passed


''' This helper function combines the previous two helpers and serves as a sanity check before we run the main search algorithm. You could ignore this part. '''
def check_configs(configs, expected_num_vert, expected_score_1, expected_score_2):
    check_config_unbounded(configs, expected_score_1, expected_score_2)
    check_config_vertices(configs, expected_num_vert)





# Helper functions that are important and used in the main search algorithm. 

# Checks whether the set of edges is a matching in graph G
def is_valid_matching(edges, G):
    used_nodes = set()
    for u, v in edges:
        if u in used_nodes or v in used_nodes:
            return False
        if not G.has_edge(u, v):
            return False
        used_nodes.add(u)
        used_nodes.add(v)
    return True

# Returns all maximum matchings in a graph G. 

def all_max_matchings(G):
    edges = list(G.edges())
    n = len(G.nodes)
    # Try all edge subsets of size up to n//2 (max matching size)
    for r in range(n // 2, 0, -1):
        found = []
        for candidate in combinations(edges, r):
            if is_valid_matching(candidate, G):
                found.append(set(candidate))
        if found:
            return found
    return []

# The function below determines whether a matching indeed matches every trisector on a bisector to exactly 2 views. It returns True if and only if there is a correct way of labeling the trisectors such that each trisector is contained in a correct bisector configuration. 

def is_clean_matching(matching):
    trisector_to_bisectors = {}

    for u, v in matching:
        tri_node, b_node = (u, v) if u.startswith("Tri") else (v, u)

        if not tri_node.startswith("Tri") or not b_node.startswith("B"):
            continue  # not a trisector-bisector match

        # Extract info
        tri_base, _ = tri_node.split("_")  
        b_base = b_node.split("_")[0]           

        key = tri_base 

        if key not in trisector_to_bisectors:
            trisector_to_bisectors[key] = set()
        trisector_to_bisectors[key].add(b_base)

    for views in trisector_to_bisectors.values():
        if len(views) == 1:
            return False 

    return True






# Below are related to the input configurations, which are represented in corresponding yaml files

def load_configs_from_yaml(file_path):
    with open(file_path, 'r') as f:
        raw_configs = yaml.safe_load(f)

    configs = []
    for item in raw_configs:
        name = item.get("name")
        num_nvd_faces = item.get("num_nvd_faces")

        blue = item["blue"]
        red = item["red"]

        blue_gt = GenericTrisector(
            label_M=blue["label_M"],
            label_U=blue["label_U"],
            label_L=blue["label_L"]
        )

        red_gt = GenericTrisector(
            label_M=red["label_M"],
            label_U=red["label_U"],
            label_L=red["label_L"]
        )

        configs.append(Config(
            blue=blue_gt,
            red=red_gt,
            name=name,
            num_nvd_faces=num_nvd_faces
        ))

    return configs

def add_to_label(label, amount):
    match = re.match(r"^(\d+)([nf]?)$", label)
    if not match:
        raise ValueError(f"Invalid label format: {label}")
    num = int(match.group(1))
    suffix = match.group(2)
    return f"{num + amount}{suffix}"

def modify_config_labels(config, operations, amount=2):

    new_config = {
        "name": config.name + "_modified" if config.name else None,
        "num_nvd_faces": config.num_nvd_faces,
        "blue": {
            "label_M": config.blue.label_M,
            "label_U": config.blue.label_U,
            "label_L": list(config.blue.label_L)
        },
        "red": {
            "label_M": config.red.label_M,
            "label_U": config.red.label_U,
            "label_L": list(config.red.label_L)
        }
    }

    for color, field in operations:
        field = field.strip().upper()
        if field in ["M", "U"]:
            key = f"label_{field}"
            original = new_config[color][key]
            new_config[color][key] = add_to_label(original, amount)
        elif field.startswith("L"):
            try:
                index = int(field[1])
                original = new_config[color]["label_L"][index]
                new_config[color]["label_L"][index] = add_to_label(original, amount)
            except (IndexError, ValueError):
                raise ValueError(f"Invalid L field index in: '{field}'")
        else:
            raise ValueError(f"Unknown field: '{field}'")

    return new_config


class QuotedStr(str): pass

def quoted_presenter(dumper, data):
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='"')

yaml.add_representer(QuotedStr, quoted_presenter)

def to_yaml_list_entry(config_dict):

    def wrap(obj):
        if isinstance(obj, dict):
            return {k: wrap(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [wrap(i) for i in obj]
        elif isinstance(obj, str):
            return QuotedStr(obj)
        else:
            return obj

    wrapped = wrap(config_dict)

    return yaml.dump(
        [wrapped],  # wrap in a list to get leading `-` format
        sort_keys=False,
        default_flow_style=False,
        width=100  
    )


def parse_single_command(command_str):
    command_str = command_str.lower().replace("add", "").strip()
    parts = [p.strip() for p in command_str.split("and")]
    result = []

    for part in parts:
        tokens = part.split()
        if len(tokens) != 2:
            raise ValueError(f"Invalid command part: {part}")
        color, field = tokens
        result.append((color, field))
    return result


def apply_multiple_modifications(config, command_input, amount=2):
    if isinstance(command_input, str):
        command_strings = [s.strip() for s in command_input.split(";")]
    else:
        command_strings = command_input

    # Collect all operations
    operations = []
    for cmd in command_strings:
        operations.extend(parse_single_command(cmd))

    # Start with the original config
    return modify_config_labels(config, operations, amount)




def same_config_except_name(c1, c2):
    def compare_trisectors(t1, t2):
        return (
            t1.label_M == t2.label_M and
            t1.label_U == t2.label_U and
            set(t1.label_L) == set(t2.label_L)
        )

    return (
        c1.num_nvd_faces == c2.num_nvd_faces and
        (
            (compare_trisectors(c1.blue, c2.blue) and compare_trisectors(c1.red, c2.red)) or
            (compare_trisectors(c1.blue, c2.red) and compare_trisectors(c1.red, c2.blue))
        )
        and extract_third_digit(c1.name) == extract_third_digit(c2.name)
    )

def find_duplicate_configs(configs):
    matching_pairs = []
    for c1, c2 in combinations(configs, 2):
        if c1.name != c2.name and same_config_except_name(c1, c2):
            matching_pairs.append((c1.name, c2.name))
    return matching_pairs


def shorten_configs(config_name):
    with open(config_name, "r") as f:
        raw_data = yaml.safe_load(f)    
    configs = load_configs_from_yaml(config_name)

    duplicate_pairs = find_duplicate_configs(configs)
    
    to_comment = set()
    rename_map = {}
    
    for a_name, b_name in duplicate_pairs:
        to_comment.add(b_name)
        # If a is already renamed, append b
        if a_name in rename_map:
            rename_map[a_name] += f"={b_name}"
        else:
            rename_map[a_name] = f"{a_name}={b_name}"

    output_lines = []
    
    for config in raw_data:
        name = config.get("name")
    
        if name in to_comment:
            # Comment out the entire block
            block = yaml.dump([config], sort_keys=False, default_flow_style=False)
            commented = "\n".join(f"# {line}" for line in block.strip().splitlines())
            output_lines.append(commented)
        else:
            # Rename if needed
            if name in rename_map:
                config["name"] = rename_map[name]
            block = yaml.dump([config], sort_keys=False, default_flow_style=False)
            output_lines.append(block.strip())
    
    name, ext = os.path.splitext(config_name)
    new_name = f"{name}_short{ext}"
    
    with open(new_name, "w") as f:
        f.write("\n\n".join(output_lines) + "\n")
    

def add_twist_and_write(helper_dict, configs, repeat_num, output):
        
    try:
        with open(output, "r") as f:
            existing_text = f.read()
    except FileNotFoundError:
        existing_text = ""
        
    output_lines = existing_text.strip().splitlines() if existing_text else []

    for config in configs:
        base_name = config.name
    
        if base_name not in helper_dict:
            continue
    
        command_list = [[cmd] for cmd in helper_dict[base_name]]
        commands_combinations = list(product(command_list, repeat=repeat_num))  # can change repeat
    
        for i, command_tuple in enumerate(commands_combinations, 1):
            combined_commands = list(chain.from_iterable(command_tuple))
            comment_line = "# " + " + ".join(combined_commands)
    
            updated_dict = apply_multiple_modifications(config, combined_commands)
            updated_dict["name"] = f"{base_name}_{i}"
    
            # Dump YAML string and split to insert line-by-line
            yaml_str = yaml.dump([updated_dict], sort_keys=False).strip()
            yaml_lines = yaml_str.splitlines()
    
            # Append comment + YAML block
            output_lines.append(comment_line)
            output_lines.extend(yaml_lines)
    
    # Write everything back to file
    with open(output, "w") as f:
        f.write("\n".join(output_lines) + "\n")
    





''' The main exhaustive search algorithm. It assumes the following labeling of the bisectors and trisectors, see the comments in the function. tri1 consists of the configuration for bisector B(1,2), B(1,3), B(2,3) in this order, they are tri1[0], tri1[1], tri1[2] respectively. s is the "special" trisector that induce 0 vertex in the case of (0,4,4,4) or 6 vertices in the case of (6,2,2,2). The trisector that is special is set to be T(1,2,3). '''

def get_valid_comb(configs, confign, num_of_v, case):
    triplets_s = list(combinations_with_replacement(configs, 3))
    triplets_n = list(product(confign, repeat=3))

    if case == 2226:
        s = 6
    else:
        s = 0

    num_success = 0
    # Assume that the special trisector is T(1,2,3)
    for i, tri1 in enumerate(triplets_s):
        # tri1 consists of the configuration for bisector B(1,2), B(1,3), B(2,3) in this order, they
        # are tri1[0], tri1[1], tri1[2] respectively.

        primary = tri1[0].blue if unbounded_generic_trisector(tri1[0].blue) == s else tri1[0].red
        secondary = tri1[0].red if primary is tri1[0].blue else tri1[0].blue
        Trisector123 = trisector_from_generic(primary)
        Trisector124 = trisector_from_generic(secondary)
    
        # Next, checkout what the view of T(1,2,3) is on B(1,3)
        is_blue_primary = unbounded_generic_trisector(tri1[1].blue) == s
        active = tri1[1].blue if is_blue_primary else tri1[1].red
        passive = tri1[1].red if is_blue_primary else tri1[1].blue
        # Check for view match
        if matches_view(active, TrisectorView(Trisector123, "B")):
            remaining_view = "C"
        elif matches_view(active, TrisectorView(Trisector123, "C")):
            remaining_view = "B"
        else:
            continue
        Trisector134 = trisector_from_generic(passive)

        # Next, checkout what the view of T(1,2,3) is on B(2,3)
        if unbounded_generic_trisector(tri1[2].blue) == s:
            if not matches_view(tri1[2].blue, TrisectorView(Trisector123, remaining_view)):
                continue
            Trisector234 = trisector_from_generic(tri1[2].red)
        else:
            if not matches_view(tri1[2].red, TrisectorView(Trisector123, remaining_view)):
                continue
            Trisector234 = trisector_from_generic(tri1[2].blue)
   
        for _, tri2 in enumerate(triplets_n):
        # tri2 consists of the configuration for bisector B(1,4), B(2,4), B(3,4) in this order.
        # We create a simple bipartite graph to detect whether there is a compatible assignment
        # and furthermore, if we wish, how many.

            # Checks the total number of faces
            if tri2[0].num_nvd_faces+tri2[1].num_nvd_faces+tri2[2].num_nvd_faces+tri1[0].num_nvd_faces+tri1[1].num_nvd_faces+tri1[2].num_nvd_faces != num_of_v + 9:
                continue

            # Checks the parallel condition
            if extract_third_digit(tri1[0].name)*extract_third_digit(tri1[1].name)*extract_third_digit(tri2[0].name) != 1:
                continue
            if extract_third_digit(tri1[0].name)*extract_third_digit(tri1[2].name)*extract_third_digit(tri2[1].name) != 1:
                continue
            if extract_third_digit(tri1[1].name)*extract_third_digit(tri1[2].name)*extract_third_digit(tri2[2].name) != 1:
                continue
            if extract_third_digit(tri2[0].name)*extract_third_digit(tri2[1].name)*extract_third_digit(tri2[2].name) != 1:
                continue

            # Below checks whether there is a way of matching the trisectors with the bisector configurations
            aux_graph = nx.Graph()
            trisector_map = {
                "124": Trisector124,
                "134": Trisector134,
                "234": Trisector234
            }

            bisectors = ["B14", "B24", "B34"]
            trisectors_per_bisector = {
                "B14": ["124", "134"],
                "B24": ["124", "234"],
                "B34": ["234", "134"]
            }

            for i, bisector in enumerate(bisectors):
                for color in ["red", "blue"]:
                    source = f"{bisector}_{color}"
                    config = getattr(tri2[i], color)

                    for tri_name in trisectors_per_bisector[bisector]:
                        target_trisector = trisector_map[tri_name]
                        for view in ["B", "C"]:
                            target = f"Tri{tri_name}_{view}"
                            if matches_view(config, TrisectorView(target_trisector, view)):
                                aux_graph.add_edge(source, target)

            all_matches = all_max_matchings(aux_graph)
            valid_matches = [m for m in all_matches if is_clean_matching(m) and len(m) == 6]
            if valid_matches:
                num_success += 1
                print(f"Configuration tuple {num_success}")
                print(f"    B(1,2): {tri1[0].summary()}, B(1,3): {tri1[1].summary()}, B(2,3): {tri1[2].summary()}.")
                print(f"    B(1,4): {tri2[0].summary()}, B(2,4): {tri2[1].summary()}, B(3,4): {tri2[2].summary()}.\n")
            

    print(f"The total number of possible configuration tuple is {num_success}.")
        
