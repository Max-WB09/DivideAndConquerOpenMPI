#include <errno.h>
#include <limits.h>
#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void bubble_sort(int *v, int n);
void intercala(int *v, int n, int *aux);

enum { DATA = 1, RESULT = 2 };

static void die(const char *message)
{
    fprintf(stderr, "%s\n", message);
    MPI_Abort(MPI_COMM_WORLD, 1);
}

static int *allocate(int n)
{
    int *p = malloc((size_t)n * sizeof(*p));
    if (!p) die("falha ao alocar vetor");
    return p;
}

static int parse_positive(const char *s)
{
    char *end;
    errno = 0;
    long value = strtol(s, &end, 10);
    if (errno || *s == '\0' || *end || value < 1 || value > INT_MAX)
        die("n deve ser inteiro positivo até INT_MAX");
    return (int)value;
}

/* O tamanho é obtido da própria mensagem, nunca enviado separadamente. */
static int *receive_vector(int parent, int *n)
{
    MPI_Status status;
    MPI_Probe(parent, DATA, MPI_COMM_WORLD, &status);
    MPI_Get_count(&status, MPI_INT, n);
    if (*n < 1) die("mensagem com tamanho inválido");
    int *v = allocate(*n);
    MPI_Recv(v, *n, MPI_INT, parent, DATA, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
    return v;
}

/* Árvore binária completa: filhos 2r+1 e 2r+2, pai (r-1)/2. */
static void original(int rank, int n, int *v, int *aux, int delta, int size)
{
    if (n <= delta) {
        if (2 * (long long)rank + 1 < size)
            die("delta encerrou a árvore antes de usar todos os ranks");
        bubble_sort(v, n);
        return;
    }
    int left = 2 * rank + 1, right = left + 1;
    if (right >= size) die("delta exige filhos inexistentes");
    int half = n / 2;
    MPI_Send(v, half, MPI_INT, left, DATA, MPI_COMM_WORLD);
    MPI_Send(v + half, n - half, MPI_INT, right, DATA, MPI_COMM_WORLD);
    MPI_Recv(v, half, MPI_INT, left, RESULT, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
    MPI_Recv(v + half, n - half, MPI_INT, right, RESULT, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
    intercala(v, n, aux);
}

/* Intervalo contíguo de ranks: a raiz local fica com a esquerda e envia a
 * direita ao rank base + ceil(span/2). Funciona também com P=31. */
static void balanced(int base, int span, int n, int *v, int *aux)
{
    if (span == 1) {
        bubble_sort(v, n);
        return;
    }
    int left_span = (span + 1) / 2;
    int helper = base + left_span;
    int half = n / 2;
    MPI_Send(v + half, n - half, MPI_INT, helper, DATA, MPI_COMM_WORLD);
    balanced(base, left_span, half, v, aux);
    MPI_Recv(v + half, n - half, MPI_INT, helper, RESULT, MPI_COMM_WORLD,
             MPI_STATUS_IGNORE);
    intercala(v, n, aux);
}

/* Cada ajudante descobre o pai e o tamanho de sua subárvore apenas pelo rank. */
static void balanced_group(int rank, int size, int *parent, int *span)
{
    int base = 0, width = size;
    while (base != rank) {
        int left = (width + 1) / 2;
        if (rank < base + left) {
            width = left;
        } else {
            *parent = base;
            base += left;
            width -= left;
        }
    }
    *span = width;
}

int main(int argc, char **argv)
{
    MPI_Init(&argc, &argv);
    int rank, size;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);
    if (argc != 4 || (strcmp(argv[1], "original") && strcmp(argv[1], "balanced")))
        die("uso: mpirun -np P ./mpi_sort original n delta | balanced n P");
    int n_total = parse_positive(argv[2]);
    int is_original = strcmp(argv[1], "original") == 0;
    int leaves = (size + 1) / 2;
    int parameter = parse_positive(argv[3]);
    if (is_original && ((size & (size + 1)) != 0 ||
                        (size > 1 && n_total < 2 * leaves)))
        die("original requer P=2^k-1 e, se P>1, n >= 2*folhas");
    if (!is_original && n_total < size)
        die("balanced requer n >= P");
    int delta = is_original ? parameter : 0;
    if (is_original && delta != (n_total - 1) / leaves + 1)
        die("delta deve ser ceil(n/folhas) para esta configuração");
    if (!is_original && parameter != size)
        die("P informado deve coincidir com MPI_Comm_size");

    int parent = -1, span = size, n = n_total;
    if (rank != 0) {
        if (is_original) parent = (rank - 1) / 2;
        else balanced_group(rank, size, &parent, &span);
    }
    int *v = rank == 0 ? allocate(n_total) : NULL;
    if (rank == 0)
        for (int i = 0; i < n_total; ++i) v[i] = n_total - i;

    MPI_Barrier(MPI_COMM_WORLD);
    double start = rank == 0 ? MPI_Wtime() : 0.0;
    if (rank != 0) v = receive_vector(parent, &n);
    int *aux = allocate(n);
    if (is_original) original(rank, n, v, aux, delta, size);
    else balanced(rank, span, n, v, aux);
    if (rank != 0) {
        MPI_Send(v, n, MPI_INT, parent, RESULT, MPI_COMM_WORLD);
    } else {
        double elapsed = MPI_Wtime() - start;
        int valid = 1;
        for (int i = 0; i < n_total; ++i)
            if (v[i] != i + 1) { valid = 0; break; }
        printf("modo=%s n=%d delta=%d processos=%d tempo=%.6f verificacao=%s\n",
               argv[1], n_total, delta, size, elapsed, valid ? "OK" : "ERRO");
        fflush(stdout);
        if (!valid) MPI_Abort(MPI_COMM_WORLD, 2);
    }
    free(aux);
    free(v);
    const char *report_placement = getenv("T3_REPORT_PLACEMENT");
    if (report_placement && strcmp(report_placement, "1") == 0) {
        char host[MPI_MAX_PROCESSOR_NAME] = {0};
        int host_len;
        MPI_Get_processor_name(host, &host_len);
        char *hosts = rank == 0 ? calloc((size_t)size, MPI_MAX_PROCESSOR_NAME) : NULL;
        if (rank == 0 && !hosts) die("falha ao alocar mapa de nós");
        MPI_Gather(host, MPI_MAX_PROCESSOR_NAME, MPI_CHAR,
                   hosts, MPI_MAX_PROCESSOR_NAME, MPI_CHAR, 0, MPI_COMM_WORLD);
        if (rank == 0) {
            printf("placement=");
            for (int i = 0; i < size; ++i) {
                const char *name = hosts + (size_t)i * MPI_MAX_PROCESSOR_NAME;
                int first = 1, count = 0;
                for (int j = 0; j < size; ++j) {
                    const char *other = hosts + (size_t)j * MPI_MAX_PROCESSOR_NAME;
                    if (strcmp(name, other) == 0) {
                        ++count;
                        if (j < i) first = 0;
                    }
                }
                if (first) printf("%s%s:%d", i ? "," : "", name, count);
            }
            printf("\n");
            free(hosts);
        }
    }
    MPI_Finalize();
    return 0;
}
