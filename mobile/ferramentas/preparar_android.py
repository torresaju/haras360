"""Completa a pasta android/ gerada pelo `flutter create` com as configurações do Haras360.

Uso (no GitHub Actions, dentro de mobile/):
    flutter create --platforms=android --org br.com.haras360 --project-name haras360 .
    python3 ferramentas/preparar_android.py

O que muda:
* Identificador br.com.haras360.campo, nome "Haras360", Android 8.0 ou superior (API 26).
* Assinatura de release pela chave Android do Ricardo, lida das variáveis H360_KEYSTORE,
  H360_KEYSTORE_SENHA, H360_CHAVE_ALIAS e H360_CHAVE_SENHA (vindas dos segredos do GitHub).
  Sem elas, o build usa a chave de depuração e o APK não deve ser publicado.
* Permissões: internet, câmera, microfone (áudio nos registros) e estado da rede. HTTP liberado porque o servidor ainda é
  acessado por IP sem HTTPS (risco registrado na especificação).
* Leitor de QR Code pelo Google Play Services (APK menor) e ícone do app.
* App do gestor (v1.5.0): avisos no celular (POST_NOTIFICATIONS, desugaring exigido pelo
  flutter_local_notifications) e digital ou PIN (USE_BIOMETRIC e FlutterFragmentActivity, exigida pelo local_auth).
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
    s = trocar(s, r"^(\s*)compileOptions\s*\{", r"\1compileOptions {\n\1    coreLibraryDesugaringEnabled true", "compileOptions")
    s = s.rstrip() + "\n\ndependencies {\n    coreLibraryDesugaring 'com.android.tools:desugar_jdk_libs:2.1.4'\n}\n"
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
    s = trocar(s, r"^(\s*)compileOptions\s*\{", r"\1compileOptions {\n\1    isCoreLibraryDesugaringEnabled = true", "compileOptions")
    s = s.rstrip() + '\n\ndependencies {\n    coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.1.4")\n}\n'
    p.write_text(s, encoding="utf-8")


def manifesto():
    p = ANDROID / "app" / "src" / "main" / "AndroidManifest.xml"
    s = p.read_text(encoding="utf-8")
    if "usesCleartextTraffic" in s:
        return
    perms = "\n".join(f'    <uses-permission android:name="android.permission.{x}"/>'
                      for x in ("INTERNET", "CAMERA", "ACCESS_NETWORK_STATE", "RECORD_AUDIO", "POST_NOTIFICATIONS", "USE_BIOMETRIC"))
    s = re.sub(r"(<manifest[^>]*>)", r"\1\n" + perms, s, count=1)
    s = re.sub(r'android:label="[^"]*"', 'android:label="Haras360"', s, count=1)
    s = s.replace("<application", '<application\n        android:usesCleartextTraffic="true"', 1)
    p.write_text(s, encoding="utf-8")


def atividade():
    # local_auth (digital ou PIN do app do gestor) exige FlutterFragmentActivity.
    for p in (ANDROID / "app" / "src" / "main").rglob("MainActivity.*"):
        s = p.read_text(encoding="utf-8")
        if "FlutterFragmentActivity" not in s:
            s = s.replace("io.flutter.embedding.android.FlutterActivity", "io.flutter.embedding.android.FlutterFragmentActivity")
            s = re.sub(r"\bFlutterActivity\(\)", "FlutterFragmentActivity()", s)
            s = re.sub(r"extends FlutterActivity\b", "extends FlutterFragmentActivity", s)
            if "FlutterFragmentActivity" not in s:
                falhar(f"não consegui trocar a atividade em {p.name}")
            p.write_text(s, encoding="utf-8")
        return
    falhar("MainActivity não encontrada")


def propriedades():
    # Leitor de QR Code pelo ML Kit do Google Play Services (não embutido): o APK fica bem menor.
    # Sem o Play Services, o caseiro digita o código mostrado abaixo do QR Code.
    p = ANDROID / "gradle.properties"
    s = p.read_text(encoding="utf-8")
    if "mobile_scanner.useUnbundled" not in s:
        p.write_text(s.rstrip() + "\ndev.steenbakker.mobile_scanner.useUnbundled=true\n", encoding="utf-8")


def icone():
    origem = RAIZ / "recursos" / "icone"
    for pasta in origem.iterdir():
        destino = ANDROID / "app" / "src" / "main" / "res" / pasta.name
        destino.mkdir(parents=True, exist_ok=True)
        shutil.copy(pasta / "ic_launcher.png", destino / "ic_launcher.png")


if __name__ == "__main__":
    gradle()
    manifesto()
    atividade()
    propriedades()
    icone()
    print("android/ preparado: br.com.haras360.campo, API 26+, assinatura por variáveis de ambiente, permissões e ícone.")
