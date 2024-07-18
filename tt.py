if __name__ == '__main__':
    from treelib import Tree
    t = Tree()
    t.create_node('root', 'root')
    include = ['pubscene', 'pubscene.journey', 'pubscene.journey.mine', 'pubscene.journey.journeycls', 'pubscene.usage','taskscene', 'taskscene.journey', 'taskscene.journey.journeycls']
    for inc in include:
        inc_list = inc.split('.')
        if not t.contains(inc_list[0]):
            t.create_node(inc_list[0], inc_list[0], parent='root')
        if len(inc_list) == 1: continue
        if not t.contains('.'.join(inc_list[:2])):
            t.create_node(inc_list[1], '.'.join(inc_list[:2]), parent=inc_list[0])
        if len(inc_list) == 2: continue
        print(t.get_node('.'.join(inc_list[:2])).data)
        t.create_node(inc_list[2], '.'.join(inc_list), parent='.'.join(inc_list[:2]))

    t.show()

    print([t[node].identifier for node in t.expand_tree(mode=Tree.WIDTH, sorting=False)])

    for node in t.expand_tree(mode=Tree.WIDTH, sorting=False):
        print(node)

    print([(t[node].data, node) for node in t.expand_tree(mode=Tree.WIDTH, sorting=False)])

    print([node.tag for node in t.children('pubscene')])













