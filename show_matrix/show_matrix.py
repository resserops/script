import argparse
import os
import sys
import subprocess
import time
import math

import numpy
import matplotlib.pyplot as xplot
import matplotlib.colors as xcolors

# 配置选项
m_resolution = 120
matrixes = ('G2_circuit.mtx',)

# 基本信息
script_name = os.path.basename(sys.argv[0])
script_name_0 = os.path.splitext(script_name)[0]
script_dir = os.path.dirname(os.path.realpath(sys.argv[0]))

current_path = os.getcwd()
root_path = os.path.realpath(os.sep)
home_path = os.path.realpath(os.path.expanduser('~'))

# 定义colormap
norm_delta = 0.6 # 控制颜色分布区间，区间为矩阵非零元密度的+-delta
colors = [(1, 1, 0.5), (0.5, 1, 1), (0, 0.5, 1), (0, 0, 0)]
matrix_colormap = xcolors.LinearSegmentedColormap.from_list('matrix_colormap', colors, N=100) # N代表采样数量，整条colormap的颜色数量
matrix_colormap.set_under('white')

# 解析入参
aparser = argparse.ArgumentParser()
aparser.add_argument('-i', '--input', default=None)
aparser.add_argument('--colorbar', action='store_true', default=False)
opts = aparser.parse_args()

def draw_colormap(colormap):
    data = numpy.random.rand(10, 10)
    xplot.imshow(data, cmap=colormap)
    xplot.colorbar()

def print_baseinfo():
    print('Script:', script_name, ' '.join(sys.argv[1:]))
    print('Script  path:', script_dir)
    print('Current path:', current_path, '\n')

def proc_shell(cmd, capture=False):
    stdout = subprocess.PIPE if capture else None
    stderr = subprocess.STDOUT if capture else None
    ret = subprocess.run(cmd, shell=True, stdout=stdout, stderr=stderr, encoding='utf-8')
    return ret.returncode, ret.stdout

def create_itv_mapping(src, dst):
    a = (dst[1] - dst[0]) / (src[1] - src[0])
    def func(x):
        return dst[0] + (x - src[0]) * a
    return func

def draw_matrix(output):
    output_sp = output.splitlines()
    line0 = output_sp[0].split()
    
    assert(len(line0) == 5)
    m, n, m_rate, n_rate, n_resolution = [int(x) for x in line0]

    mat = numpy.zeros((m_resolution, n_resolution))
    nnz = 0
    for line in output_sp[1:]:
        if len(line) == 0:
            continue
        line_sp = line.split()
        assert(len(line_sp) == 3)
        x, y, count = [int(x) for x in line_sp]
        mat[x, y] = count / (m_rate * n_rate) # src矩阵非零元密度
        nnz += count

    extent = (0, n_rate * n_resolution, m_rate * m_resolution, 0)
    d = nnz / (m * n) # 整体非零元密度
    d_ln = math.log(d)
    d_min = math.e ** ((1 + norm_delta) * d_ln)
    d_max = math.e ** ((1 - norm_delta) * d_ln)
    normalize = xcolors.LogNorm(vmin=d_min, vmax=d_max, clip=False)
    xplot.imshow(mat, cmap=matrix_colormap, extent=extent, norm=normalize)
    if opts.colorbar:
        xplot.colorbar()
    xplot.xticks([])
    xplot.yticks([])
    xplot.subplots_adjust(wspace=0, hspace=0)

if __name__ == '__main__':
    print_baseinfo()

    if opts.input:
        mat_list = opts.input.split(os.pathsep)
    else:
        mat_list = matrixes

    def to_realpath(mat):
        rpath_based_script = f'{script_dir}{os.sep}{mat}'
        if os.path.isfile(rpath_based_script):
            return os.path.realpath(rpath_based_script)

        rpath_based_current = f'{current_path}{os.sep}{mat}'
        if os.path.isfile(rpath_based_current):
            return os.path.realpath(rpath_based_current)
        
        return None

    # 构建core程序，加速大量数据处理
    os.chdir(script_dir)
    build_cmd = f'g++ -std=c++17 -O3 core.cc mmio.c -o core'
    proc_shell(build_cmd, True)

    for mat in matrixes:
        mat_bak = mat
        if not os.path.isabs(mat):
            mat = to_realpath(mat)
        if mat == None or not os.path.isfile(mat):
            print(f'Error: Matrix {mat_bak} not found.')
            continue

        assert(' ' not in mat)
        mat_name = os.path.basename(mat)
        mat_name = os.path.splitext(mat_name)[0]
        
        print(f'Process matrix {mat_name}...')
        t0 = time.time()

        core_cmd = f'{script_dir}{os.sep}core {mat} {m_resolution}'
        rc, output = proc_shell(core_cmd, True)
        t1 = time.time()
        print(f'Matrix reading and compression done. Cost: {t1 - t0}s')
        
        draw_matrix(output)
        xplot.savefig(f'{script_dir}{os.sep}{mat_name}.png', bbox_inches='tight', pad_inches=0)
        xplot.clf()
        t2 = time.time()
        print(f'Draw image done. Cost: {t2 - t1}s')
        print()
