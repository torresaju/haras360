"""Completa a pasta android/ gerada pelo `flutter create` com as configurações do Haras360.

Uso (no GitHub Actions, dentro de mobile/):
    flutter create --platforms=android --org br.com.haras360 --project-name haras360 .
    python3 ferramentas/preparar_android.py

O que muda:
* Identificador br.com.haras360.campo, nome "Haras360", Android 8.0 ou superior (API 26).
* Assinatura de release pela chave Android do Ricardo, lida das variáveis H360_KEYSTORE,
  H360_KEYSTORE_SENHA, H360_CHAVE_ALIAS e H360_CHAVE_SENHA (vindas dos segredos do GitHub).
  Sem elas, o build usa a chave de depuração e o APK não deve ser publicado.
* Permissões: internet, câmera e estado da rede. HTTP liberado porque o servidor ainda é
  acessado por IP sem HTTPS (risco registrado na especificação).
* Ícone do app.
"""
import re
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ANDROID = RAIZ / "android"


def falhar(msg):
    sys.exit(f"preparar_android: {msg}")


def trocar(texto, padrao, novo, nome, obrigatorio=True):
    t, n = re.subn(padrao, novo, texto, count=1, flags=re.M)
    if n == 0 and obrigatorio:
        falhar(f"não encontrei {nome!r} no build.gradle gerado pelo Flutter")
    return t


def gradle():
    p = ANDROID / "app" / "build.gradle"
    kts = ANDROID / "app" / "build.gradle.kts"
    if kts.exists() and not p.exists():
        return gradle_kts(kts)
    if not p.exists():
        falhar("android/app/build.gradle não existe. Rode flutter create antes.")
    s = p.read_text(encoding="utf-8")
    if "H360_KEYSTORE" in s:
        return
    s = trocar(s, r'applicationId\s*=?\s*"[^"]+"', 'applicationId = "br.com.haras360.campo"', "applicationId")
    s = trocar(s, r"minSdk(Version)?\s*=?\s*[\w.]+", "minSdk = 26", "minSdk")
    assinatura = '''
    signingConfigs {
        release {
            def ks = System.getenv("H360_KEYSTORE")
            if (ks != null && !ks.isEmpty()) {
                storeFile = file(ks)
                storeType = "pkcs12"
                storePassword = System.getenv("H360_KEYSTORE_SENHA")
                keyAlias = System.getenv("H360_CHAVE_ALIAS")
                keyPassword = System.getenv("H360_CHAVE_SENHA")
            }
        }
    }

    buildTypes {'''
    s = trocar(s, r"^\s*buildTypes\s*\{", assinatura, "buildTypes")
    s = trocar(s, r"signingConfig\s*=?\s*signingConfigs\.debug",
               'signingConfig = System.getenv("H360_KEYSTORE") ? signingConfigs.release : signingConfigs.debug', "signingConfig")
    p.write_text(s, encoding="utf-8")


def gradle_kts(p):
    s = p.read_text(encoding="utf-8")
    if "H360_KEYSTORE" in s:
        return
    s = trocar(s, r'applicationId\s*=\s*"[^"]+"', 'applicationId = "br.com.haras360.campo"', "applicationId")
    s = trocar(s, r"minSdk\s*=\s*[\w.]+", "minSdk = 26", "minSdk")
    assinatura = '''
    signingConfigs {
        create("release") {
            val ks = System.getenv("H360_KEYSTORE")
            if (!ks.isNullOrEmpty()) {
                storeFile = file(ks)
                storeType = "pkcs12"
                storePassword = System.getenv("H360_KEYSTORE_SENHA")
                keyAlias = System.getenv("H360_CHAVE_ALIAS")
                keyPassword = System.getenv("H360_CHAVE_SENHA")
            }
        }
    }

    buildTypes {'''
    s = trocar(s, r"^\s*buildTypes\s*\{", assinatura, "buildTypes")
    s = trocar(s, r'signingConfig\s*=\s*signingConfigs\.getByName\("debug"\)',
               'signingConfig = if (System.getenv("H360_KEYSTORE").isNullOrEmpty()) signingConfigs.getByName("debug") else signingConfigs.getByName("release")',
               "signingConfig")
    p.write_text(s, encoding="utf-8")


def manifesto():
    p = ANDROID / "app" / "src" / "main" / "AndroidManifest.xml"
    s = p.read_text(encoding="utf-8")
    if "usesCleartextTraffic" in s:
        return
    perms = "\n".join(f'    <uses-permission android:name="android.permission.{x}"/>' for x in ("INTERNET", "CAMERA", "ACCESS_NETWORK_STATE"))
    s = re.sub(r"(<manifest[^>]*>)", r"\1\n" + perms, s, count=1)
    s = re.sub(r'android:label="[^"]*"', 'android:label="Haras360"', s, count=1)
    s = s.replace("<application", '<application\n        android:usesCleartextTraffic="true"', 1)
    p.write_text(s, encoding="utf-8")


def icone():
    origem = RAIZ / "recursos" / "icone"
    for pasta in origem.iterdir():
        destino = ANDROID / "app" / "src" / "main" / "res" / pasta.name
        destino.mkdir(parents=True, exist_ok=True)
        shutil.copy(pasta / "ic_launcher.png", destino / "ic_launcher.png")


if __name__ == "__main__":
    gradle()
    manifesto()
    icone()
    print("android/ preparado: br.com.haras360.campo, API 26+, assinatura por variáveis de ambiente, permissões e ícone.")
