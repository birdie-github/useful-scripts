; file: cat.asm
; usage: ./cat <file>

; build instructions:
; nasm -f elf64 minicat.asm -o minicat.o
; ld -static -o minicat minicat.o

global _start

section .bss
    buffer resb 4096

section .text

_start:
    ; argc is at [rsp]
    mov rdi, [rsp]        ; argc
    cmp rdi, 2
    jne exit              ; need exactly 1 argument

    ; argv[1] is at [rsp+16]
    mov rdi, [rsp+16]     ; filename pointer

    ; open(filename, O_RDONLY, 0)
    mov rax, 2            ; sys_open
    xor rsi, rsi          ; O_RDONLY = 0
    xor rdx, rdx          ; mode = 0
    syscall

    cmp rax, 0
    js exit               ; error

    mov r12, rax          ; save fd

read_loop:
    ; read(fd, buffer, 4096)
    mov rax, 0            ; sys_read
    mov rdi, r12
    lea rsi, [rel buffer]
    mov rdx, 4096
    syscall

    cmp rax, 0
    jle close_file        ; 0 = EOF, <0 = error

    ; write(1, buffer, bytes_read)
    mov rdx, rax          ; count
    mov rax, 1            ; sys_write
    mov rdi, 1            ; stdout
    lea rsi, [rel buffer]
    syscall

    jmp read_loop

close_file:
    ; close(fd)
    mov rax, 3            ; sys_close
    mov rdi, r12
    syscall

exit:
    mov rax, 60           ; sys_exit
    xor rdi, rdi
    syscall
