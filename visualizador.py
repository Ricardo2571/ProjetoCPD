import pygame
import random
import sys

# Importa a tua classe cliente do ficheiro que já criaste
from cliente import RPCClient

# --- CONFIGURAÇÕES VISUAIS ---
TAMANHO_CELULA = 10  # Tamanho de cada quadrado em pixeis
LINHAS = 60
COLUNAS = 80
FPS = 10  # Velocidade da simulação (Gerações por segundo)

# Cores
COR_FUNDO = (30, 30, 30)
COR_CELULA_VIVA = (50, 200, 50)
COR_TEXTO = (255, 255, 255)
COR_FUNDO_TEXTO = (0, 0, 0)


def desenhar_grelha(ecra, grid):
    ecra.fill(COR_FUNDO)
    for r in range(LINHAS):
        for c in range(COLUNAS):
            if grid[r][c] == 1:
                x = c * TAMANHO_CELULA
                y = r * TAMANHO_CELULA
                pygame.draw.rect(ecra, COR_CELULA_VIVA, (x, y, TAMANHO_CELULA, TAMANHO_CELULA))


def main():
    print("A ligar ao Servidor RPC...")
    cliente = RPCClient(host='localhost', port=5000)

    # Gerar a grelha inicial
    grid = [[1 if random.random() < 0.2 else 0 for _ in range(COLUNAS)] for _ in range(LINHAS)]

    # Inicializar o Pygame e Fontes
    pygame.init()
    ecra = pygame.display.set_mode((COLUNAS * TAMANHO_CELULA, LINHAS * TAMANHO_CELULA))
    pygame.display.set_caption("Game of Life RPC - Paralelo")
    relogio = pygame.time.Clock()
    fonte = pygame.font.SysFont("consolas", 18, bold=True)

    # Variáveis de Estado
    geracao = 0
    workers = 1  # Começa com 1 workers por defeito
    pausa = True  # Começa pausado para poderes escolher os workers!
    a_correr = True

    print("\nSimulação iniciada! Controlos na Janela:")
    print("- [ESPAÇO]: Pausar/Retomar")
    print("- [CIMA] / [BAIXO]: Aumentar/Diminuir Workers")
    print("- [R]: Reiniciar grelha aleatória")
    print("- [ESC]: Sair")

    while a_correr:
        # 1. Processar Eventos do Teclado
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                a_correr = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    a_correr = False
                elif event.key == pygame.K_SPACE:
                    pausa = not pausa
                elif event.key == pygame.K_UP:
                    workers += 1  # Aumenta os workers
                elif event.key == pygame.K_DOWN:
                    workers = max(1, workers - 1)  # Impede que desça abaixo de 1
                elif event.key == pygame.K_r:
                    # Reinicia a grelha
                    grid = [[1 if random.random() < 0.2 else 0 for _ in range(COLUNAS)] for _ in range(LINHAS)]
                    geracao = 0

        # 2. Desenhar a Grelha
        desenhar_grelha(ecra, grid)

        # 3. Desenhar o Painel de Informação (HUD)
        estado_txt = "PAUSADO" if pausa else "A CORRER"
        texto = f" Estado: {estado_txt} | Geracao: {geracao} | Workers: {workers} (Use Setas Cima/Baixo) "
        imagem_texto = fonte.render(texto, True, COR_TEXTO)

        # Desenha um fundo preto por trás do texto para ser legível
        fundo_rect = (5, 5, imagem_texto.get_width(), imagem_texto.get_height())
        pygame.draw.rect(ecra, COR_FUNDO_TEXTO, fundo_rect)
        ecra.blit(imagem_texto, (5, 5))

        pygame.display.flip()

        # 4. Comunicação com o Servidor (Apenas se não estiver em pausa)
        if not pausa:
            nova_grid = cliente.call("game_of_life", {
                "grid": grid,
                "generations": 1,
                "workers": workers  # Envia o número ATUALIZADO de workers para o servidor!
            })

            if nova_grid:
                grid = nova_grid
                geracao += 1
            else:
                print("Erro de comunicação com o servidor.")
                a_correr = False

        # 5. Controlo da taxa de atualização
        relogio.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == '__main__':
    main()