#!/usr/bin/env python
import os
import re
import sys


def replace_emojis_in_file(file_path):
    """Substitui emojis em um arquivo por suas versões em texto."""
    with open(file_path, 'r', encoding='utf-8') as file:
        try:
            content = file.read()
        except UnicodeDecodeError:
            print(
                f"Erro ao ler arquivo {file_path} com UTF-8. Tentando com latin-1...")
            with open(file_path, 'r', encoding='latin-1') as file2:
                content = file2.read()

    # Dicionário de substituições
    replacements = {
        "✅": "[OK]",
        "❌": "[ERRO]",
        "🚀": "[INICIO]",
        "📸": "[FOTO]",
        "🔍": "[BUSCA]",
        "\u2705": "[OK]",    # ✅ em unicode
        "\U0001f680": "[INICIO]",  # 🚀 em unicode
        "\U0001f4f8": "[FOTO]",    # 📸 em unicode
        "\U0001f50d": "[BUSCA]"    # 🔍 em unicode
    }

    # Realizar as substituições
    changed = False
    for emoji, replacement in replacements.items():
        if emoji in content:
            content = content.replace(emoji, replacement)
            changed = True

    # Salvar apenas se houver mudanças
    if changed:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)
        print(f"Arquivo modificado: {file_path}")
        return True
    return False


def process_directory(directory):
    """Processa todos os arquivos Python em um diretório recursivamente."""
    total_modified = 0
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                if replace_emojis_in_file(file_path):
                    total_modified += 1
    return total_modified


if __name__ == "__main__":
    target_directory = './automation_py'
    if len(sys.argv) > 1:
        target_directory = sys.argv[1]

    print(f"Processando arquivos Python em: {target_directory}")
    modified = process_directory(target_directory)
    print(f"Total de arquivos modificados: {modified}")
