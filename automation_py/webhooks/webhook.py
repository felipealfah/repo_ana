from flask import Flask, request, jsonify
import logging
import json
import os
import time
from threading import Thread
import requests

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Caminho para armazenar dados dos SMS recebidos
SMS_DATA_DIR = "sms_data"
os.makedirs(SMS_DATA_DIR, exist_ok=True)

# Armazenamento em memória para códigos SMS recebidos
sms_codes = {}


@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint para verificar se o serviço está funcionando."""
    return jsonify({"status": "ok"})


@app.route('/sms-webhook', methods=['POST'])
def sms_webhook():
    """Endpoint para receber notificações de SMS da API SMS-Activate."""
    try:
        # Verificar se a requisição é um JSON
        if request.is_json:
            data = request.json
        else:
            # Se não for JSON, tentar processar como form data
            data = request.form.to_dict()

        logger.info(f"📩 Webhook recebido: {data}")

        # Extrair informações importantes
        activation_id = data.get('id')
        phone_number = data.get('phone')
        sms_code = data.get('sms')
        status = data.get('status')

        # Validar dados obrigatórios
        if not all([activation_id, sms_code]):
            logger.warning(f"⚠️ Dados incompletos no webhook: {data}")
            return jsonify({"success": False, "error": "Dados incompletos"}), 400

        # Armazenar o código SMS
        sms_codes[activation_id] = {
            "phone_number": phone_number,
            "sms_code": sms_code,
            "status": status,
            "received_at": time.time()
        }

        # Salvar em arquivo para persistência
        save_sms_data(activation_id, sms_codes[activation_id])

        # Processar o código SMS recebido em uma thread separada
        # para não bloquear a resposta ao webhook
        Thread(target=process_sms_code, args=(
            activation_id, phone_number, sms_code, status)).start()

        # Retornar sucesso imediatamente
        return jsonify({"success": True, "message": "SMS recebido e processado"})

    except Exception as e:
        logger.error(f"[ERRO] Erro ao processar webhook: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


def save_sms_data(activation_id, data):
    """Salva dados do SMS em arquivo para persistência."""
    try:
        file_path = os.path.join(SMS_DATA_DIR, f"{activation_id}.json")
        with open(file_path, 'w') as f:
            json.dump(data, f)
        logger.info(f"[OK] Dados do SMS {activation_id} salvos com sucesso")
    except Exception as e:
        logger.error(f"[ERRO] Erro ao salvar dados do SMS: {str(e)}")


def process_sms_code(activation_id, phone_number, sms_code, status):
    """
    Processa um código SMS recebido via webhook.
    Esta função pode realizar ações como:
    - Notificar outro serviço
    - Atualizar status em banco de dados
    - Fazer callback para o sistema principal
    """
    try:
        logger.info(f"⚙️ Processando SMS para ativação {activation_id}")

        # Verificar se há uma URL de callback configurada para esta ativação
        # (isso seria configurado quando o número é comprado)
        callback_url = get_callback_url(activation_id)

        if callback_url:
            # Enviar o código SMS para o callback
            response = requests.post(callback_url, json={
                "activation_id": activation_id,
                "phone_number": phone_number,
                "sms_code": sms_code,
                "status": status
            }, timeout=10)

            if response.status_code == 200:
                logger.info(
                    f"[OK] Código SMS enviado para callback: {callback_url}")
            else:
                logger.error(
                    f"[ERRO] Erro ao enviar para callback: {response.status_code} - {response.text}")
        else:
            logger.info(
                f"ℹ️ Nenhum callback configurado para ativação {activation_id}")

        # Registrar processamento bem-sucedido
        update_sms_status(activation_id, "processed")

    except Exception as e:
        logger.error(f"[ERRO] Erro ao processar código SMS: {str(e)}")
        update_sms_status(activation_id, "failed", str(e))


def get_callback_url(activation_id):
    """
    Recupera a URL de callback para uma ativação específica.
    Implementação simplificada - em um sistema real, isso buscaria de um banco de dados.
    """
    # Exemplo: buscar de um arquivo de configuração
    try:
        config_path = os.path.join(SMS_DATA_DIR, "callbacks.json")
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                callbacks = json.load(f)
                return callbacks.get(activation_id)
    except Exception:
        pass
    return None


def update_sms_status(activation_id, status, error=None):
    """Atualiza o status de processamento de um SMS."""
    try:
        if activation_id in sms_codes:
            sms_codes[activation_id]["processing_status"] = status
            if error:
                sms_codes[activation_id]["processing_error"] = error

            # Atualizar o arquivo
            save_sms_data(activation_id, sms_codes[activation_id])
    except Exception as e:
        logger.error(f"[ERRO] Erro ao atualizar status do SMS: {str(e)}")


@app.route('/sms-status/<activation_id>', methods=['GET'])
def get_sms_status(activation_id):
    """Endpoint para verificar o status de um SMS pelo ID de ativação."""
    if activation_id in sms_codes:
        return jsonify(sms_codes[activation_id])
    else:
        # Tentar carregar do arquivo
        file_path = os.path.join(SMS_DATA_DIR, f"{activation_id}.json")
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                return jsonify(data)
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500

        return jsonify({"success": False, "error": "Activation ID not found"}), 404


if __name__ == '__main__':
    # Iniciar o servidor em modo de produção
    # Em ambiente de produção, use um servidor WSGI como Gunicorn
    port = int(os.environ.get("PORT", 5001))
    app.run(host='0.0.0.0', port=port)
