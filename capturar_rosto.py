"""
Script auxiliar para capturar amostras de rosto usadas no treinamento do
reconhecimento facial (item 7 do assistente).

Rode este script uma vez para cada pessoa que a assistente deve reconhecer.
DICA do professor: rode também pelo menos uma vez com o nome "desconhecido",
usando fotos de outras pessoas/ângulos, para melhorar a precisão do modelo.

Uso:
    python capturar_rosto.py
"""

import os

import cv2

PASTA_FOTOS = os.path.join("rostos", "fotos")
NUMERO_MAX_AMOSTRAS = 25
TAMANHO_AMOSTRA = (220, 220)


def capturar_amostras(nome):
    """Captura NUMERO_MAX_AMOSTRAS fotos do rosto da pessoa informada."""
    os.makedirs(PASTA_FOTOS, exist_ok=True)
    classificador = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    camera = cv2.VideoCapture(0)
    amostra = 1

    print("Olhe para a câmera e pressione 'q' repetidas vezes até completar as amostras.")
    while amostra <= NUMERO_MAX_AMOSTRAS:
        ok, imagem = camera.read()
        if not ok:
            break

        cinza = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
        faces = classificador.detectMultiScale(cinza, scaleFactor=1.05, minSize=(150, 150))

        for (x, y, largura, altura) in faces:
            cv2.rectangle(imagem, (x, y), (x + largura, y + altura), (0, 0, 255), 2)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                rosto = cv2.resize(cinza[y:y + altura, x:x + largura], TAMANHO_AMOSTRA)
                caminho = os.path.join(PASTA_FOTOS, f"{nome}_{amostra}.jpg")
                cv2.imwrite(caminho, rosto)
                print(f"Amostra {amostra}/{NUMERO_MAX_AMOSTRAS} salva.")
                amostra += 1

        cv2.imshow("Captura de rosto", imagem)

    camera.release()
    cv2.destroyAllWindows()
    print(f"Captura de '{nome}' concluída.")


if __name__ == "__main__":
    nome_pessoa = input("Digite o nome da pessoa (ou 'desconhecido' para amostras negativas): ").strip()
    capturar_amostras(nome_pessoa)
