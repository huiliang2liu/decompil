#!/usr/bin/python3

import os
import re
import sys
import json
import shutil
import manifest


def decompil(apk, save_path, apktool):
    print(apk)
    print(save_path)
    cmd = 'java -jar %s d "%s" -o %s' % (apktool, apk, save_path)
    os.system(cmd)


def statistical_file(path):
    files = os.listdir(path)
    fileList = []
    for file in files:
        file = os.path.join(path, file)
        if os.path.isfile(file):
            if not str(file).endswith('.smali'):
                continue
            fileList.append(file)
            continue
        child_dir = statistical_file(file)
        if len(child_dir) <= 0:
            continue
        for child in child_dir:
            fileList.append(child)
    return fileList


def print_file(files, js, save_file=None, save_dir=None, save_des=None):
    dirs = []
    fs = []
    for file in files:
        if os.sep != '/':
            file = file.replace(os.sep, '/')
        m = re.match(r'.*smali[^/]*/(.*)', file)
        if m:
            file = m.group(1).replace('/', '.')
            fs.append(file)
            m = re.match(r'(.*)\.[^\.]*\.smali', file)
            if m:
                file = m.group(1)
                if file not in dirs:
                    dirs.append(file)
    if save_file:
        with open(save_file, 'w') as f:
            for file in fs:
                f.writelines(file)
                f.writelines('\n')
    else:
        print(fs)

    if save_dir:
        with open(save_dir, 'w') as f:
            for d in dirs:
                f.writelines(d)
                f.writelines('\n')
    else:
        print(dirs)
    if save_des:
        with open(save_des, 'w', encoding='utf-8') as f:
            for key in js.keys():
                for file in dirs:
                    if str(file).startswith(key):
                        f.writelines(js[key])
                        f.writelines('\n')
                        break
    else:
        for key in js.keys():
            for file in dirs:
                if str(file).startswith(key):
                    print(js[key])
                    break


def ver_code(ver):
    ss = str(ver).split('.')
    power = len(ss) - 1
    if len(ss) < 1:
        return 0
    vc = 0
    for i in range(len(ss)):
        vc += int(ss[i]) * 100 ** (power - i)
    return vc


def deal_apk(apk):
    name = str(os.path.basename(apk)).replace('.apk', '')
    print('正在处理%s' % name)
    save_path = os.path.join(path, name).replace(' ', '')
    if os.path.isdir(save_path):
        shutil.rmtree(save_path)
    if apktool:
        decompil(os.path.join(path, apk), save_path, apktool)
    else:
        decompil(os.path.join(path, apk), save_path)
    files = statistical_file(save_path)
    save_file = os.path.join(path, '%s_file.txt' % name)
    save_dir = os.path.join(path, '%s_dir.txt' % name)
    save_des = os.path.join(path, '%s_des.txt' % name)
    save_manifest = os.path.join(path, '%s_manifest.txt' % name)
    with open(save_manifest, 'w') as f:
        f.writelines(json.dumps(manifest.parse_manifest(os.path.join(save_path, 'AndroidManifest.xml'))))
    print_file(files, js, save_file, save_dir, save_des)
    shutil.rmtree(save_path)
    print('处理完成%s' % name)


def deal_dir(js, path):
    files = os.listdir(path)
    for file in files:
        if not str(file).endswith('_dir.txt'):
            continue
        with open(os.path.join(path, file), 'r') as f:
            dirs = f.readlines()
        with open(str(os.path.join(path, file)).replace('_dir.txt', '_des.txt'), 'w') as f:
            for key in js.keys():
                for dir in dirs:
                    if str(dir).startswith(key):
                        f.writelines(js[key])
                        f.writelines('\n')
                        break


def merge_code(files):
    fm = {}
    for file in files:
        if 'dir.txt' not in file:
            continue
        m = re.match(r'(.*?)(([0-9]+\.+)+[0-9]{1,2}).*', file)
        if m:
            key = m.group(1)
            if key not in fm:
                fm[key] = [{'name': m.group(0), 'verCode': ver_code(m.group(2)), 'ver': m.group(2)}]
            else:
                fm[key].append({'name': m.group(0), 'verCode': ver_code(m.group(2)), 'ver': m.group(2)})
    return fm


def index(ls, entity):
    if len(ls) <= 0:
        return 0
    for i in range(len(ls)):
        var = entity['verCode']
        tar = ls[i]['verCode']
        if tar > var:
            return i
    return len(ls)


def sort(ls):
    sort_lis = []
    for entity in ls:
        sort_lis.insert(index(sort_lis, entity), entity)
    return sort_lis


def compare_file(source, tar):
    removes = []
    adds = []
    source_lines = []
    tar_lines = []
    with open(source, 'r', encoding='utf-8') as f:
        source_lines = f.readlines()
    with open(tar, 'r', encoding='utf-8') as f:
        tar_lines = f.readlines()
    # print(source_lines)
    # print(tar_lines)
    for line in source_lines:
        if line not in tar_lines:
            removes.append(line)
    for line in tar_lines:
        if line not in source_lines:
            adds.append(line)
    return removes, adds


def intersection(source, tar):
    inter = []
    for s in source:
        if s in tar:
            inter.append(s)
    return inter


def intersection_start(source, tar):
    inter = []
    for s in source:
        for t in tar:
            if str(s).startswith(t):
                inter.append(t)
                break
    return inter


def diff_set(source, tar):
    diff = []
    for s in source:
        if s in tar:
            continue
        diff.append(s)
    return diff


def diff_set_start(source, tar):
    diff = []
    for s in source:
        has = False
        for t in tar:
            if str(s).startswith(str(t)):
                has = True
                break
        if not has:
            diff.append(s)
    return diff


def list2att(js, list):
    att = []
    for key in js.keys():
        for l in list:
            if str(l).startswith(key):
                att.append(js[key])
                break
    return att


def compare(js, path, name, ls):
    keys = js.keys()
    for i in range(len(ls) - 1):
        source = ls[i]
        tar = ls[i + 1]
        with open(os.path.join(path, source['name']), 'r') as f:
            source_lines = f.readlines()
        with open(os.path.join(path, tar['name']), 'r') as f:
            tar_lines = f.readlines()
        inter = intersection(source_lines, tar_lines)
        source_att_lines = list2att(js, source_lines)
        tar_att_lines = list2att(js, tar_lines)
        inter_att = intersection(source_att_lines, tar_att_lines)
        diff_set_source = diff_set(source_lines, inter)
        diff_set_tar = diff_set(tar_lines, inter)
        diff_set_source_att = diff_set(source_att_lines, inter_att)
        diff_set_tar_att = diff_set(tar_att_lines, inter_att)
        file = os.path.join(path, '%s_%s_%s_change.txt' % (name, source['ver'], tar['ver']))
        with open(os.path.join(path, source['name']).replace('_dir.txt', '_manifest.txt'), 'r') as f:
            source_manifest = json.load(f)
        with open(os.path.join(path, tar['name']).replace('_dir.txt', '_manifest.txt'), 'r') as f:
            tar_manifest = json.load(f)
        with open(file, 'w', encoding='utf-8') as f:
            diff_set_source_ = diff_set_start(diff_set_source, keys)
            f.writelines('移除了\n\n')
            for line in diff_set_source_:
                f.writelines(line)
            f.writelines("\n增加了\n\n")
            diff_set_source_ = diff_set_start(diff_set_tar, keys)
            for line in diff_set_source_:
                f.writelines(line)
            f.writelines('\n移除的属性\n\n')
            for line in diff_set_source_att:
                f.writelines('%s\n' % line)
            f.writelines('\n增加的属性\n\n')
            for line in diff_set_tar_att:
                f.writelines('%s\n' % line)
            f.writelines('\n更新的数据\n\n')
            diff_set_source_ = diff_set(diff_set_tar, diff_set_source_)
            for line in diff_set(list2att(js, diff_set_source_), diff_set_tar_att):
                f.writelines('%s\n' % line)
            source_application = source_manifest['application']
            tar_application = tar_manifest['application']
            if source_application == tar_application:
                f.writelines('\napplication节点没有修改\n')
            else:
                f.writelines('\napplication节点节点修改前:%s\n' % source_application)
                f.writelines('\napplication节点修改后:%s\n' % tar_application)
            source_permissions = source_manifest['permissions']
            tar_permissions = tar_manifest['permissions']
            inter = intersection(source_permissions, tar_permissions)
            f.writelines('\n删除的权限\n\n')
            for line in diff_set(source_permissions, inter):
                f.writelines('%s\n' % line)
            f.writelines('\n添加的权限\n\n')
            for line in diff_set(tar_permissions, inter):
                f.writelines('%s\n' % line)
            source_permissions = source_manifest['activities']
            tar_permissions = tar_manifest['activities']
            inter = intersection(source_permissions, tar_permissions)
            f.writelines('\n删除的activity\n\n')
            for line in diff_set(source_permissions, inter):
                f.writelines('%s\n' % line)
            f.writelines('\n添加的activity\n\n')
            for line in diff_set(tar_permissions, inter):
                f.writelines('%s\n' % line)
            source_permissions = source_manifest['providers']
            tar_permissions = tar_manifest['providers']
            inter = intersection(source_permissions, tar_permissions)
            f.writelines('\n删除的provider\n\n')
            for line in diff_set(source_permissions, inter):
                f.writelines('%s\n' % line)
            f.writelines('\n添加的provider\n\n')
            for line in diff_set(tar_permissions, inter):
                f.writelines('%s\n' % line)
            source_permissions = source_manifest['services']
            tar_permissions = tar_manifest['services']
            inter = intersection(source_permissions, tar_permissions)
            f.writelines('\n删除的service\n\n')
            for line in diff_set(source_permissions, inter):
                f.writelines('%s\n' % line)
            f.writelines('\n添加的service\n\n')
            for line in diff_set(tar_permissions, inter):
                f.writelines('%s\n' % line)
            source_permissions = source_manifest['receivers']
            tar_permissions = tar_manifest['receivers']
            inter = intersection(source_permissions, tar_permissions)
            f.writelines('\n删除的receiver\n\n')
            for line in diff_set(source_permissions, inter):
                f.writelines('%s\n' % line)
            f.writelines('\n添加的receiver\n\n')
            for line in diff_set(tar_permissions, inter):
                f.writelines('%s\n' % line)
        # file = os.path.join(path, '%s_%s_%s_change.txt' % (name, source['ver'], tar['ver']))
        # removes, adds = compare_file(os.path.join(path, source['name']), os.path.join(path, tar['name']))
        # remove_att, add_att = compare_file(os.path.join(path, source['name']).replace('_dir.txt', '_des.txt'),
        #                                    os.path.join(path, tar['name']).replace('_dir.txt', '_des.txt'))
        # inter_att = intersection(remove_att, add_att)
        # remove_att_inter = intersection_start(removes, keys)
        # add_att_inter = intersection_start(adds, keys)
        # print(list2att(js, remove_att_inter))
        # print(list2att(js, add_att_inter))
        # inter_change_att = intersection(list2att(js, remove_att_inter), list2att(js, add_att_inter))
        # print(remove_att)
        # print(add_att)
        # with open(file, 'w', encoding='utf-8') as f:
        #     remove_att = list2att(js, removes)
        #     add_att = list2att(js, adds)
        #     removes = diff_set(removes, diff_set_start(removes, keys))
        #     adds = diff_set(adds, diff_set_start(adds, keys))
        #     f.writelines('移除了\n\n')
        #     for line in removes:
        #         f.writelines(line)
        #     f.writelines("\n增加了\n\n")
        #     for line in adds:
        #         f.writelines(line)
        #     f.writelines('\n移除的属性\n\n')
        #     remove_att = diff_set(remove_att, inter_att)
        #     for line in remove_att:
        #         f.writelines(line)
        #         f.writelines('\n')
        #     f.writelines('\n增加的属性\n\n')
        #     add_att = diff_set(add_att, inter_att)
        #     for line in add_att:
        #         f.writelines(line)
        #         f.writelines('\n')
        #
        #     f.writelines('\n版本变更\n\n')
        #     for line in inter_change_att:
        #         f.writelines(line)
        #         f.writelines('\n')


if __name__ == '__main__':
    '''
    使用说明：先切换到main.py说在的目录直接运行main.py 然后将文件目录输入
    例如apk保存的文件目录为 /Users/liuhuiliang/work/decompil/test
    chmod +x main.py
    ./main.py /Users/liuhuiliang/work/decompil/test
    如果apktool使用自己的目录则需要输入文件地址
    例如
    ./main.py /Users/liuhuiliang/work/decompil/test /Users/liuhuiliang/work/decompil/jar/apktool_2.4.1.jar
    '''
    if len(sys.argv) < 2:
        print('''
    使用说明：先切换到main.py说在的目录直接运行main.py 然后将文件目录输入
    例如apk保存的文件目录为 /Users/liuhuiliang/work/decompil/test
    chmod +x main.py
    ./main.py /Users/liuhuiliang/work/decompil/test
    如果apktool使用自己的目录则需要输入文件地址
    例如
    ./main.py /Users/liuhuiliang/work/decompil/test /Users/liuhuiliang/work/decompil/jar/apktool_2.4.1.jar
    ''')
    else:
        js = None
        deal = True
        if len(sys.argv) > 3:
            deal = sys.argv[3]
            if str(deal).lower() == 'false':
                deal = False
        with open('table.json', 'r', encoding='utf-8') as f:
            js = json.load(f)
        apktool = None
        if len(sys.argv) > 2:
            apktool = sys.argv[2]
        else:
            apktool = os.path.join(os.getcwd(), "jar")
            apktool = os.path.join(apktool, "apktool_2.4.1.jar")
        path = sys.argv[1]
        if deal:
            files = os.listdir(path)
            for apk in files:
                if not str(apk).endswith('.apk'):
                    continue
                deal_apk(apk)
        else:
            deal_dir(js, path)
        files = os.listdir(path)
        fm = merge_code(files)
        for key in fm.keys():
            sort_list = sort(fm[key])
            compare(js, path, key, sort_list)
            # print(key)
            # print(fm[key])
