# Trabalho 3: divisão e conquista com MPI

O código implementa a ordenação proposta no enunciado em `docs/`. O vetor começa
em ordem decrescente, as folhas usam Bubble Sort e os processos internos
intercalam as duas partes ordenadas. Em toda execução, a raiz confere que o
resultado é exatamente `1, 2, ..., n` e imprime `verificacao=OK`.

## Compilar e validar

```bash
make all
make check
```

`make check` usa `mpirun` e verifica casos pequenos. Em ambientes que bloqueiam
sockets, a execução MPI precisa ocorrer fora desse isolamento.

## Modos

```bash
bin/sequencial 40000                  # T1: Bubble Sort do vetor inteiro
bin/sequencial 40000 10000            # T1': árvore original com delta=10000
bin/sequencial 40000 --balanced 31    # T1': árvore balanceada de 31 processos
mpirun -np 7 bin/mpi_sort original 40000 10000
mpirun -np 31 bin/mpi_sort balanced 40000 31
```

Na árvore original, `P=2^k-1`, o pai de rank `r>0` é `(r-1)/2` e seus filhos são
`2r+1` e `2r+2`. O programa exige `delta=ceil(2n/(P+1))` e, para P>1, `n >= P+1`,
para que todas as folhas previstas recebam trabalho. O pai envia **ambas** as
metades antes de receber resultados. Ele usa `MPI_Probe` e `MPI_Get_count` para
obter o tamanho do vetor recebido.

Na árvore balanceada, cada processo guarda a metade esquerda e manda a direita
ao rank `base+ceil(span/2)`, onde `base` é o primeiro rank da subárvore e `span`
seu número de processos. O processo continua trabalhando na esquerda enquanto
o ajudante ordena a direita. Para `P=31`, as folhas podem receber tamanhos
diferentes. A referência sequencial `--balanced 31` percorre exatamente as
mesmas divisões. Para inspecionar a carga de cada folha:

```bash
python3 scripts/tree_loads.py 40000 31
```

## Medições no Atlântica

Envie o job a partir da raiz deste repositório:

```bash
sbatch scripts/experimentos.sbatch
```

O job reserva dois nós exclusivos, registra o `lscpu` de cada um e mantém essa
alocação durante todas as medições. Ele calibra `n` para que uma execução de T1
dure de 30 a 60 segundos. Se o tamanho já foi escolhido, use:

```bash
sbatch --export=ALL,N=40000 scripts/experimentos.sbatch
```

Cada configuração é repetida 10 vezes. São medidos T1, a referência sequencial
da árvore correspondente, a versão original com 1, 3, 7, 15 e 31 processos,
a balanceada com 2, 4, 8, 16, 31 e 32 processos, e a original com 63, 127,
255, 511 e 1023 processos tanto com `OMPI_MCA_mpi_yield_when_idle=0` quanto
com `=1`. Os processos são distribuídos entre os dois nós, com diferença máxima
de um processo; o mapa real é registrado em `placement.tsv`. O caso P=1 ocupa
um nó dentro da reserva exclusiva dos dois nós.

Os arquivos ficam em `result/<job_id>/`:

- `raw.tsv`: todos os tempos brutos e verificações;
- `executions.log`: a saída completa de cada execução, identificada por modo,
  processos, repetição e configuração de espera;
- `summary.csv`: mediana, mínimo, máximo, ganho de algoritmo, dois speed-ups e
  eficiência para cada configuração paralela;
- `placement.tsv`: distribuição real dos ranks entre nós na primeira repetição;
- `nodes.txt`, `lscpu.txt`, `metadata.txt`, `calibration.log`: contexto da execução;
- `plots/`: gráficos PNG de tempos, speed-ups, eficiência e espera ativa versus
  cessão do núcleo.

O stdout e stderr do Slurm ficam em `result/slurm-<job_id>.out` e `.err`. O
diretório `result/` já existe no repositório, pois o Slurm precisa dele antes
de iniciar o job.

Os gráficos são gerados automaticamente ao fim do job se `matplotlib` estiver
disponível. Caso contrário, instale a dependência e gere depois:

```bash
python3 -m pip install -r requirements-plot.txt
python3 scripts/plot.py result/<job_id>/summary.csv
```

Na tabela resumida, `speedup_bubble=T1/TP`, `speedup_tree=T1'/TP` e
`algorithm_gain=T1/T1'`. A eficiência é `speedup_tree/P`; para P acima de 32
na série original, o denominador é 32 threads de hardware, conforme o enunciado.
Os tempos de referência usam a mediana das 10 repetições correspondentes.

## Limites da região medida

A raiz inicializa o vetor antes de sincronizar os processos. O tempo MPI começa
logo após a barreira, antes do primeiro envio, e termina quando a raiz recebe
e intercala o vetor completo. A verificação e a coleta do mapa de nós ficam
fora da região medida. A versão sequencial mede apenas a ordenação.
