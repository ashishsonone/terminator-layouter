import sys 
import os
import argparse
import random
import json
import yaml

def exit():
    sys.exit(0)

def get_arg_name(key):
    return key.replace('-', '_')

def print_usage():
    parser.print_help()
    exit()

parser = argparse.ArgumentParser()
parser.add_argument('--input-file', '-i', default=None)
parser.add_argument('--assist', '-a', action="store_true")

args = parser.parse_args()
args = vars(args)

help = args.get('assist', False)
if help:
    print_usage() #exits

input_file = args[get_arg_name('input-file')] or ''
if not input_file:
    print('--input-file param required. Aborting...')
    print_usage() #exits

print('Working on input file {}'.format(input_file))

#=============================
import re
id_regex = r'\[\[\[(\w+)\]\]\]'
def find(input, regex):
    m = re.search(regex, input)
    return m and m.group(1)

clean_regex = r'[^\w]'
def clean(input):
    if type(input) == type(""):
        return re.sub(clean_regex, '', input)
    return None

def parse_layout_children(lines):
    children = []
    current = None
    for line in lines:
        line = line.strip()
        #print('line : {}'.format(line))
        if line.strip()[:3] == '[[[':
            #new child
            _id = find(line, id_regex)
            #print('old child = {}'.format(current))
            current = {}
            current['id'] = _id
            #print('new child = {}'.format(current))
            children.append(current)
        else:
            #extract and store property in current child
            #key = value
            tokens = line.split(' = ')
            key = tokens[0]
            value = tokens[1]
            current[key] = value
    print('all children = {}'.format(len(children)))
    return children

def nest(children):
    nested_map = {}
    window_child_id = None

    #put in map so that order doesn't matter
    for child in children:
        child_id = child['id']
        nested_map[child_id] = child
        child['babies'] = []

    #do the actual work
    for child in children:
        child_id = child['id']
        if child.get('type', None) == 'Window':
            window_child_id = child_id
        parent_id = child.get('parent', None)
        parent_id = clean(parent_id)
        if parent_id:
            parent = nested_map[parent_id]
            parent['babies'].append(child_id)

    #sort the chilren within each node
    for child in children:
        child['babies'].sort(key=lambda nid : nested_map[nid]['order'])

    return nested_map, window_child_id

def print_structure(node_id, nested_map, indent=0):
    node = nested_map[node_id]
    print('{}{} [{}] : {}'.format(' ' * indent, node['order'], node['type'], node['id']))

    for child_id in node['babies']:
        print_structure(child_id, nested_map, indent=indent+4)

def process(input_file):
    f = open(input_file)
    lines = f.readlines()
    children = parse_layout_children(lines)
    nested_map, window_child_id = nest(children)
    print_structure(window_child_id, nested_map)

#depth : 1 : [layouts], 2 : [[default]], 3 : [[[child1]]]
#target : '*' or 'default' or 'tab1' or ...
def gen_cherry_regex(name, depth):
    if name == '*':
        name = '[\w ]+'
    name = '({})'.format(name)
    regex = '^{}{}{}'.format('\['*depth, name, '\]'*depth)
    return regex

#stripped line
def get_depth(line):
    if line[:1] == '[':
        line = find(line, '^(\\[*)')
        if line:
            return len(line)
    return -1

#assume that only lines with depth >= given depth are present
def read_targets(lines, depth):
    targets = [] #target : {name='layouts', lines=[<line>]}

    current_target = None

    cherry_regex = gen_cherry_regex('*', depth)

    for line in lines:
        s_line = line.strip()
        if not s_line:
            continue #discard empty lines

        name = find(s_line, cherry_regex)
        if name:
            #new target
            current_target = {'name' : name, 'lines' : [], 'cherry' : line}
            print('new target : {}'.format(name))
            targets.append(current_target)
        else:
            #add to current target
            current_target['lines'].append(line)
    return targets

#process(input_file)

def try_1():
    targets = read_targets(open(input_file).readlines(), 3)
    cherry = random.sample(targets, 1)[0]
    print(cherry)
    cherry['lines'].append('  hello = world -----------------------------------\n')

    for t in targets:
        print(t['cherry'], end='')
        for c in t['lines']:
            print(c, end='')

def try_2(target_layout_name):
    #full config file
    print('\nfind level 1 targets')
    targets = read_targets(open(input_file).readlines(), 1)
    cherry = [target for target in targets if target['name'] == 'layouts'][0]
    print('\nfind level 2 targets')
    layouts = read_targets(cherry['lines'], 2)
    print('\nfinding actual layouts')
    for layout in layouts:
        print('parsing layout : {}'.format(layout['name']))
        children = parse_layout_children(layout['lines'])
        nested_map, window_child_id = nest(children)
        if layout['name'] == target_layout_name:
            print_structure(window_child_id, nested_map)

idee = -1
def get_next_id():
    global idee
    idee = idee + 1
    return str(idee)

def gen_name_line(indent, name):
    return '{}[[[{}]]]'.format(' '*indent, name)

def gen_property_line(indent, key, value):
    return '{}{} = {}'.format(' '*indent, key, value)

def generate_node(parent, order, node, indent):
    out_lines = []
    if node['t'] == 'w':
        name = 'window' + get_next_id()
        out_lines.append(gen_name_line(indent, name))
        out_lines.append(gen_property_line(indent + 2, 'parent', '""'))
        out_lines.append(gen_property_line(indent + 2, 'order', order))
        out_lines.append(gen_property_line(indent + 2, 'type', 'Window'))

        out_lines.append(gen_property_line(indent + 2, 'title', node['title']))
        out_lines.append(gen_property_line(indent + 2, 'maximised', node['maximised']))
        out_lines.append(gen_property_line(indent + 2, 'fullscreen', node['fullscreen']))
        children = node['children']
        out_lines += generate_node(name, '0', children[0], indent)

    elif node['t'] == 'n':
        name = 'notebook' + get_next_id()
        out_lines.append(gen_name_line(indent, name))
        out_lines.append(gen_property_line(indent + 2, 'parent', parent))
        out_lines.append(gen_property_line(indent + 2, 'order', order))
        out_lines.append(gen_property_line(indent + 2, 'type', 'Notebook'))

        active_page = node.get('active_page', 0)
        out_lines.append(gen_property_line(indent + 2, 'active_page', '{}'.format(active_page)))
        
        children = node.get('children', [])
        labels = []
        for i in range(0, len(children)):
            child = children[i]
            label = child.get('title', None) or 'Tab:{}'.format(i)
            labels.append(label)
        out_lines.append(gen_property_line(indent + 2, 'labels', ','.join(labels)))

        for i in range(0, len(children)):
            child = children[i]
            out_lines += generate_node(name, '{}'.format(i), child, indent)

    elif node['t'] == 'h' or node['t'] == 'v':
        prefix = 'horizontal' if node['t'] == 'h' else 'vertical'
        type = 'HPaned' if node['t'] == 'v' else 'VPaned'
        #HPaned splits vertical line; VPaned splits horizontal line
        name =  prefix + get_next_id()
        out_lines.append(gen_name_line(indent, name))
        out_lines.append(gen_property_line(indent + 2, 'parent', parent))
        out_lines.append(gen_property_line(indent + 2, 'order', order))
        out_lines.append(gen_property_line(indent + 2, 'type', type))
        ratio = node.get('ratio', '0.5')
        out_lines.append(gen_property_line(indent + 2, 'ratio', ratio))

        children = node.get('children', [])
        for i in range(0, len(children)):
            child = children[i]
            out_lines += generate_node(name, '{}'.format(i), child, indent)
    elif node['t'] == 't':
        name = 'terminal' + get_next_id()
        out_lines.append(gen_name_line(indent, name))
        out_lines.append(gen_property_line(indent + 2, 'parent', parent))
        out_lines.append(gen_property_line(indent + 2, 'order', order))
        out_lines.append(gen_property_line(indent + 2, 'type', 'Terminal'))
        
        command = node.get('command', None)
        if command:
            out_lines.append(gen_property_line(indent + 2, 'command', command))

    return out_lines

#try_2('sep24')

def try_3():
    layout = yaml.load(open(input_file))
    window_layout = {}
    window_layout['t'] = 'w'
    window_layout['title'] = layout.get('window_title', '')
    window_layout['maximised'] = layout.get('window_maximised', 'True')
    window_layout['fullscreen'] = layout.get('window_fullscreen', 'False')

    notebook_layout = {}
    notebook_layout['t'] = 'n'
    notebook_layout['active_page'] = layout.get('tab_active', '0')

    window_layout['children'] = [notebook_layout]
    notebook_layout['children'] = layout['tabs']
    print(layout)
    lines = generate_node('', '0', window_layout, 4)
    for l in lines:
        print(l, end='\n')

try_3()