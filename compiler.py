from scanner import *
import re
import operator

non_terminals_set = set()
terminal_set = set()
ll1_table = {}
sentences = []
errors = open('syntax_errors.txt', 'a')
parse_tree = open('parse_tree.txt', 'a')

errors.truncate(0)
parse_tree.truncate(0)

no_error = True

def split_sentences():
    global sentences
    grammar = open('pa2grammar.txt', 'r').read()
    sentences = re.split('\n', grammar)
    for i in range(0, len(sentences)):
        sentences[i] = re.split(' -> | ', sentences[i])

def find_T_and_NTs():
    global non_terminals_set, terminal_set
    for sentence in sentences:
        non_terminals_set.add(sentence[0])
    for sentence in sentences:
        for T_or_NT in sentence:
            if T_or_NT not in non_terminals_set:
                terminal_set.add(T_or_NT)


def find_epsilon():
    is_non_terminal_goto_epsilon = {}
    is_non_terminal_goto_epsilon['ε'] = True
    for non_terminal in non_terminals_set:
        is_non_terminal_goto_epsilon[non_terminal] = False

    while(True):
        new_epsilon = False
        for sentence in sentences:
            non_terminal = sentence[0]
            if is_non_terminal_goto_epsilon[non_terminal]:
                continue
            is_goto_epsilon = True
            for T_or_NT in sentence[1:]:
                if T_or_NT not in is_non_terminal_goto_epsilon or \
                    not is_non_terminal_goto_epsilon[T_or_NT]:
                    is_goto_epsilon = False
                    break
            if is_goto_epsilon:
                is_non_terminal_goto_epsilon[non_terminal] = True
                new_epsilon = True
        if not new_epsilon:
            return is_non_terminal_goto_epsilon

def file_to_dict(file_directory):
    all_list = open(file_directory, 'r').read()
    all_list = re.split('\n', all_list)
    for i in range(0, len(all_list)):
        all_list[i] = re.split(' ', all_list[i])
    all_dict= {}
    for NT_all in all_list:
        key = NT_all[0]
        all_dict[key] = set()
        for node in NT_all[1:]:
            all_dict[key].add(node)
    return all_dict

def set_first_and_follows():
    global firsts, follows
    firsts = file_to_dict("Firsts.txt")
    for terminal in terminal_set:
        firsts[terminal] = {terminal}
    follows = file_to_dict("Follows.txt")

def create_table():
    global ll1_table
    is_non_terminal_goto_epsilon = find_epsilon()

    for non_terminal in non_terminals_set:
        ll1_table[non_terminal] = {}
    
    #handle firsts
    sentence_index = -1
    for sentence in sentences:
        sentence_index += 1
        non_terminal = sentence[0]
        for alpha in sentence[1:]:
            for terminal in firsts[alpha]:
                if terminal != 'ε':
                    ll1_table[non_terminal][terminal] = sentence_index
            if alpha not in is_non_terminal_goto_epsilon or not is_non_terminal_goto_epsilon[alpha]:
                break
    
    #handle follows
    sentence_index = -1
    for sentence in sentences:
        sentence_index += 1
        non_terminal = sentence[0]
        is_goto_epsilon = True
        for alpha in sentence:
            if alpha not in is_non_terminal_goto_epsilon or not is_non_terminal_goto_epsilon[alpha]:
                is_goto_epsilon = False
                break
        if not is_goto_epsilon:
            continue
        for terminal in follows[non_terminal]:
            if terminal not in ll1_table[non_terminal]:
                ll1_table[non_terminal][terminal] = sentence_index
    
    #handle synch
    for non_terminal in non_terminals_set:
        for terminal in follows[non_terminal]:
            if terminal not in ll1_table[non_terminal]:
                ll1_table[non_terminal][terminal] = 'synch'


def handle_error(text):
    global no_error
    if no_error:
        errors.truncate(0)
        no_error = False
    errors.write(f'#{get_line_number()} : syntax error, {text}\n')

class Tree_node():
    def __init__(self, value, width=0, parent=None):
        self.parent = parent
        self.value = value
        self.childs = []
        self.width = width
        self.depth = 0
        self.height = 0
        self.is_terminal = False
        self.token = None
    
    def add_child(self, child):
        self.childs.append(child)
        child.width = self.width + 1

    def is_leave(self):
        return len(self.childs) == 0
    
    def __str__(self):
        return str(self.value) + " " + str(self.width) + " " + str(self.depth)

    def set_token(self, token):
        self.token = token
        self.is_terminal = True

    def show(self):
        if self.is_terminal:
            return "(" + self.token[0] + ", " + self.token[1] + ") "
        if self.value == 'ε':
            return 'epsilon'
        return self.value



def ll1():
    global all_nodes, head_node
    stack = [head_node] 
    current_tocken = get_next_token()

    while True:
        X_node = stack[len(stack)-1]
        X = X_node.value
        if current_tocken[0] == 'SYMBOL':
            a = current_tocken[1]
        elif current_tocken[0] == 'ID':
            a = current_tocken[0]
        elif current_tocken[0] == 'KEYWORD':
            a = current_tocken[1]
        elif current_tocken[0] == 'NUM':
            a = current_tocken[0]
        elif current_tocken == '$':
            a = current_tocken
        
        if X == 'ε':
            stack.pop()
        elif X == a and a == '$':
            break
        elif X == a and X in terminal_set:
            stack.pop()
            X_node.set_token(current_tocken)
            current_tocken = get_next_token()
        elif X != a and X in terminal_set:
            handle_error('missing ' + X)
            node = stack.pop()
            all_nodes.remove(node)
        elif a not in ll1_table[X]:
            if a == '$':
                handle_error('unexpected EOF')
                break
            handle_error('illegal ' + a)
            current_tocken = get_next_token()
        elif ll1_table[X][a] == 'synch':
            handle_error('missing ' + X)
            node = stack.pop()
            all_nodes.remove(node)
            try:
                node.parent.childs.remove(node)
            except:
                pass
            
        else:
            sentence = sentences[ll1_table[X][a]]
            node = stack.pop()
            if len(sentence) == 1: ##
                all_nodes.remove(node)
                try:
                    node.parent.childs.remove(node)
                except:
                    pass           
            for index in range(len(sentence)-1, 0, -1):
                new_node = Tree_node(sentence[index], parent=node)
                all_nodes.append(new_node)
                stack.append(new_node)
                node.add_child(new_node)

def calculate_depth():
    global head_node
    def visit(node):
        if node.is_leave():
            return
        depth = node.depth + 1
        node.height = 0
        for index in range(len(node.childs) - 1, -1, -1):
            child = node.childs[index]
            child.depth = depth
            visit(child)
            depth += child.height + 1
            node.height += child.height + 1
    visit(head_node)

def draw_tree():
    for node in all_nodes:
        for counter in range(0, node.width - 1):
            parse_tree.write(f'│   ')
        if node.width != 0:
            parse_tree.write(f'├── ')
        parse_tree.write(f'{node.show()}\n')

if __name__ == '__main__':
    errors.write(f'There is no syntax error.')

    split_sentences()
    find_T_and_NTs()
    set_first_and_follows()
    create_table()

    head_node = Tree_node('Program')
    all_nodes = [head_node]
    ll1()

    calculate_depth()
    all_nodes.sort(key=operator.attrgetter('depth'))

    draw_tree()
