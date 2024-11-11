#include <cstdint>
#include <unordered_map>
#include <iostream>
#include <memory>
#include <algorithm>
#include <chrono>
#include <fstream>
#include <iomanip>

#include "mmio.h"

#define LIKELY(x) __builtin_expect(!!(x), 1)
#define UNLIKELY(x) __builtin_expect(!!(x), 0)

struct Mat {
    uint32_t m;
    uint32_t n;
    uint32_t nnz;
    MM_typecode type;
    std::unique_ptr<double[]> val;
    std::unique_ptr<double[]> val_imag;
    std::unique_ptr<uint32_t[]> i;
    std::unique_ptr<uint32_t[]> j;
};

Mat ReadMat(const char *input_path) {
    Mat ret;
    FILE *f{fopen(input_path, "r")};
    if (f == nullptr) {
        std::cerr << "Error: File " << input_path << " not found." << std::endl;
        exit(1);
    }
    if (mm_read_banner(f, &ret.type) != 0) {
        std::cerr << "Error: Matrix Market banner not found." << std::endl;
        exit(1);
    }
    if (!mm_is_matrix(ret.type) || !mm_is_sparse(ret.type)) {
        std::cerr << "Error: Not a sparse matrix." << std::endl;
        std::cerr << "Matrix type: " << mm_typecode_to_str(ret.type) << std::endl;
        exit(1);
    }
    if (!mm_is_real(ret.type) && !mm_is_complex(ret.type)) {
        std::cerr << "Error: Not a real or a complex matrix." << std::endl;
        std::cerr << "Matix type: " << mm_typecode_to_str(ret.type) << std::endl;
        exit(1);
    }

    int m, n, nnz;
    if ((mm_read_mtx_crd_size(f, &m, &n, &nnz)) != 0) {
        std::cerr << "Error: Parse crd size failed." << std::endl;
        exit(1);
    }
    ret.m = m;
    ret.n = n;
    ret.nnz = nnz;

    ret.val = std::make_unique<double[]>(nnz);
    if (mm_is_complex(ret.type)) {
        ret.val_imag = std::make_unique<double[]>(nnz);
    }
    ret.i = std::make_unique<uint32_t[]>(nnz);
    ret.j = std::make_unique<uint32_t[]>(nnz);

    for (size_t idx{0}; idx < nnz; ++idx) {
        if (mm_is_real(ret.type)) {
            fscanf(f, "%u %u %lf\n", &ret.i[idx], &ret.j[idx], &ret.val[idx]);
        } else if (mm_is_complex(ret.type)) {
            fscanf(f, "%u %u %lf %lf\n", &ret.i[idx], &ret.j[idx], &ret.val[idx], &ret.val_imag[idx]);
        }
        
        // 1基矩阵转0基矩阵
        --ret.i[idx];
        --ret.j[idx];
    }
    fclose(f);
    return ret;
}

auto TransMat(const char *output_path, uint32_t dst_m, const Mat &mat) {
    uint32_t dst_n{(static_cast<uint64_t>(dst_m) * mat.n + mat.m - 1) / mat.m};
    uint32_t m_rate{mat.m / dst_m};  // 每个dst矩阵i坐标对应m_rate个原矩阵i坐标
    uint32_t n_rate{mat.n / dst_n};  // 每个dst矩阵j坐标对应n_rate个原矩阵j坐标
    
    std::unordered_map<uint64_t, size_t[3]> count_map;  // size_t[2]分别保存实部、虚部、混合密度
    for (uint32_t idx{0}; idx < mat.nnz; ++idx) {
        uint32_t dst_i{std::min(dst_m - 1, mat.i[idx] / m_rate)};
        uint32_t dst_j{std::min(dst_n - 1, mat.j[idx] / n_rate)};
        uint64_t dst_coor{(static_cast<uint64_t>(dst_i)) << 32 | dst_j};

        // 针对对称矩阵，若点(i, j)在dst矩阵对角线，不在src矩阵对角线，计数+1。不在dst矩阵对角线的点压缩后处理
        size_t count{1};
        if (mm_is_symmetric(mat.type) && dst_i == dst_j && mat.i[idx] != mat.j[idx]) {
            ++count;
        }

        if (mm_is_real(mat.type)) {
            count_map[dst_coor][0] += count;
        } else {
            if (mat.val[idx] != 0) {
                count_map[dst_coor][0] += count;
            }
            if (mat.val_imag[idx] != 0) {
                count_map[dst_coor][1] += count;
            }
            count_map[dst_coor][2] += count;
        }
    }

    std::ofstream ofs(output_path);
    std::string type{mm_is_real(mat.type) ? "real" : "complex"};
    ofs << type << " " << mat.m << " " << mat.n << " " << m_rate << " " << n_rate << " " << dst_n << " " << std::endl;
    for (const auto &[k, v]: count_map) {
        uint32_t dst_i = k >> 32;
        uint32_t dst_j = k;
        ofs << dst_i << " " << dst_j << " " << v[0] << " " << v[1] << " " << v[2] << std::endl;
        // 针对对称矩阵，对不在dst矩阵对角线的点做对称处理
        if (mm_is_symmetric(mat.type) && dst_i != dst_j) {
            ofs << dst_j << " " << dst_i << " " << v[0] << " " << v[1] << " " << v[2] << std::endl;
        }
    }
}

double GetDuration(const std::chrono::system_clock::time_point &begin, const std::chrono::system_clock::time_point &end) {
    auto duration{std::chrono::duration_cast<std::chrono::microseconds>(end - begin)};
    return static_cast<double>(duration.count()) * std::chrono::microseconds::period::num / std::chrono::microseconds::period::den;
}

int main(int argc, char **argv) {
    if (argc != 4) {
        std::cout << "Error: Unexpected arg count " << argc << "." << std::endl;
        exit(1);
    }
    const char *input_path{argv[1]};
    const char *output_path{argv[2]};
    uint32_t dst_m{std::stoul(argv[3])};
    
    // 矩阵读取和数据处理
    auto t0{std::chrono::system_clock::now()};
    Mat mat{ReadMat(input_path)};
    auto t1{std::chrono::system_clock::now()};
    std::cout << std::fixed << std::setprecision(3);
    std::cout << "  Read matrix cost: " << GetDuration(t0, t1) << " s" << std::endl;
    TransMat(output_path, dst_m, mat);
    auto t2{std::chrono::system_clock::now()};
    std::cout << "  Compress matrix cost: " << GetDuration(t1, t2) << " s" << std::endl;
    return 0;
}
