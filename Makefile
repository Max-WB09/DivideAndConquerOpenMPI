CC = gcc
MPICC = mpicc
CFLAGS = -O2 -std=c11 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Wpedantic

.PHONY: all clean check
all: bin/sequencial bin/mpi_sort

bin:
	mkdir -p bin

bin/sequencial: src/sequintial/sequencial.c | bin
	$(CC) $(CFLAGS) -o $@ $<

bin/mpi_sort: src/mpi_sort.c src/sequintial/sequencial.c | bin
	$(MPICC) $(CFLAGS) -DSEQUENCIAL_NO_MAIN -o $@ $^

check: all
	python3 scripts/check.py

clean:
	rm -f bin/sequencial bin/mpi_sort
