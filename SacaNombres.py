from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time
import os
import requests
import pdfplumber
import io
import re
import concurrent.futures
import json


# 🔐 CREDENCIALES SII
RUT = ""
PASSWORD = ""

URL = "https://eboleta.sii.cl"

# 📁 NOMBRE ARCHIVO CSV
ruta_csv = os.path.expanduser("~/Downloads/EJEMPLO.csv")

options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")


options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")

# 👇 AQUÍ va la magia ahora
options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 20)
driver.get(URL) 

# =========================
# 🔐 LOGIN
# =========================

wait.until(EC.presence_of_element_located((By.ID, "inputRut"))).send_keys(RUT)
driver.find_element(By.ID, "inputPass").send_keys(PASSWORD)
boton = driver.find_element(By.ID, "bt_ingresar")
driver.execute_script("arguments[0].click();", boton)


print("🔐 Login enviado...")

# =========================
# ⏳ ESPERAR DASHBOARD
# =========================

wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
time.sleep(10)

# =========================
# 📂 ABRIR MENÚ
# =========================

menu_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//i[contains(text(),'menu')]")))
driver.execute_script("arguments[0].click();", menu_btn)

# =========================
# 📊 IR A "Resumen de ventas diarias"
# =========================

resumen_btn = wait.until(EC.element_to_be_clickable((
    By.XPATH, "//div[contains(text(),'Resumen de ventas diarias')]"
)))
driver.execute_script("arguments[0].click();", resumen_btn)

time.sleep(2)

# =========================
# 📅 ABRIR SELECTOR DE FECHA
# =========================

fecha_btn = wait.until(EC.element_to_be_clickable((
    By.XPATH, "//span[contains(@class,'v-btn__content') and contains(text(),'↷')]"
)))
driver.execute_script("arguments[0].click();", fecha_btn)

time.sleep(1)

# =========================
# 📅 DESDE
# =========================

desde = wait.until(EC.presence_of_element_located((
    By.XPATH, "//div[contains(@class,'v-date-range__picker--start')]"
)))

desde.find_element(By.XPATH, ".//div[contains(@class,'v-date-picker-title__year')]").click()
wait.until(EC.element_to_be_clickable((By.XPATH, "//li[contains(text(),'2025')]"))).click()

#Elegir Fecha desde
desde.find_element(By.XPATH, ".//div[text()='sept']").click()
desde.find_element(By.XPATH, ".//div[text()='1']").click()

# =========================
# 📅 HASTA
# =========================

hasta = wait.until(EC.presence_of_element_located((
    By.XPATH, "//div[contains(@class,'v-date-range__picker--end')]"
)))

hasta.find_element(By.XPATH, ".//div[contains(@class,'v-date-picker-title__year')]").click()
wait.until(EC.element_to_be_clickable((By.XPATH, "//li[contains(text(),'2025')]"))).click()

#Elegir fecha hasta
hasta.find_element(By.XPATH, ".//div[text()='sept']").click()
hasta.find_element(By.XPATH, ".//div[text()='30']").click()


# =========================
# ✅ CONFIRMAR
# =========================

confirmar_btn = wait.until(EC.element_to_be_clickable((
    By.XPATH, "//span[contains(text(),'Confirmar')]"
)))
driver.execute_script("arguments[0].click();", confirmar_btn)

print("📅 Filtro aplicado")

# =========================
# ⏳ ESPERAR TABLA
# =========================

time.sleep(5)

# =========================
# 📄 OBTENER FOLIOS
# =========================

filas = driver.find_elements(By.XPATH, "//tbody/tr")

for fila in filas:
    try:
        columnas = fila.find_elements(By.TAG_NAME, "td")

        if len(columnas) > 0:
            folio = columnas[0].text.strip()

            if folio.isdigit():
                print("Folio:", folio)

    except Exception as e:
        print("Error:", e)

# =========================
# 📄 OBTENER FOLIOS YA PARA GUARDAR
# =========================

# 🔓 cargar CSV existente
df = pd.read_csv(ruta_csv, sep=";")

# limpiar espacios en nombres de columnas
df.columns = df.columns.str.strip()

print("Columnas detectadas:", df.columns)

df["folio"] = df["folio"].astype(str).str.strip()

def obtener_cliente_pdf(url):
    try:
        r = requests.get(url)

        if r.status_code != 200:
            return "NO_ENCONTRADO"

        with pdfplumber.open(io.BytesIO(r.content)) as pdf:
            texto = ""
            for pagina in pdf.pages:
                texto += pagina.extract_text() or ""

        texto = re.sub(r"\n+", "\n", texto)
        lineas = texto.split("\n")

        for i, linea in enumerate(lineas):
            if "Fecha:" in linea:

                bloque = " ".join(lineas[i:i+8])
                bloque = " ".join(bloque.split())

                # =========================
                # 🧠 CASO: Santiago ... -
                # =========================
                match_santiagoo = re.search(r"Santiago\s+([A-ZÁÉÍÓÚÑ\s]+?)\s+-", bloque)
                if match_santiagoo:
                    return match_santiagoo.group(1).strip()

                # =========================
                # 🧠 CASO: Santiago ... --
                # =========================
                match_santiago = re.search(r"Santiago\s+([A-ZÁÉÍÓÚÑ\s]+?)\s+--", bloque)
                if match_santiago:
                    return match_santiago.group(1).strip()

                # =========================
                # 🧠 CASO: -- nombre Actu
                # =========================
                match_especial = re.search(r"--\s*([A-ZÁÉÍÓÚÑ\s]+?)\s+Actu", bloque)
                if match_especial:
                    return match_especial.group(1).strip()

                # =========================
                # 🧠 CASO GENERAL
                # =========================
                posibles = re.findall(r"[A-ZÁÉÍÓÚÑ\s]{5,}", bloque)

                for p in posibles:
                    candidato = p.strip()

                    candidato = re.sub(r"\b(Cod|Cons\s*Act|C:?)\b.*", "", candidato)
                    candidato = re.sub(r"\s+[A-Z]{2,}\d*-\d+.*", "", candidato)
                    candidato = re.sub(r"\s*-[A-Z]{2,}\d*.*", "", candidato)

                    candidato = candidato.strip()

                    if len(candidato.split()) >= 2:
                        return candidato
                    
        return "NO_ENCONTRADO"
    except Exception as e:
        print("Error PDF:", e)
        return "NO_ENCONTRADO"


def obtener_url_pdf():
    logs = driver.get_log("performance")

    for log in logs:
        message = json.loads(log["message"])["message"]

        if message["method"] == "Network.responseReceived":
            url = message["params"]["response"]["url"]

            if ".pdf" in url:
                return url

    return None

# =========================
# 🔁 RECORRER PAGINAS
# =========================

while True:

    time.sleep(2)

    filas = driver.find_elements(By.XPATH, "//tbody/tr")

    for fila in filas:
        try:
            columnas = fila.find_elements(By.TAG_NAME, "td")

            if len(columnas) == 0:
                continue

            folio = columnas[0].text.strip()

            if not folio.isdigit():
                continue

            print(f"📄 Folio: {folio}")

            # limpiar logs antes
            driver.get_log("performance")

            # click
            boton = fila.find_element(By.XPATH, ".//i[contains(text(),'receipt')]")
            driver.execute_script("arguments[0].click();", boton)

            # esperar carga
            time.sleep(3)

            url_pdf = obtener_url_pdf()

            if url_pdf:
                print("📎 PDF URL:", url_pdf)
                cliente = obtener_cliente_pdf(url_pdf)
            else:
                cliente = "NO_ENCONTRADO"


            print(f"👤 Cliente: {cliente}")

            # =========================
            # 💾 ACTUALIZAR CSV
            # =========================

            df.loc[df["folio"] == folio, "Cliente"] = cliente

            # cerrar modal
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            time.sleep(1)

        except Exception as e:
            print("Error:", e)

    # =========================
    # ➡️ SIGUIENTE PAGINA
    # =========================

    try:
        btn_siguiente = driver.find_element(
            By.XPATH,
            "//button[@aria-label='Página siguiente' and not(@disabled)]"
        )

        driver.execute_script("arguments[0].click();", btn_siguiente)
        print("➡️ Pasando a la siguiente página...")
        time.sleep(3)

    except:
        print("✅ No hay más páginas")
        break

# =========================
# 💾 GUARDAR CSV FINAL
# =========================

df.to_csv(ruta_csv, index=False, sep=";", encoding="utf-8-sig")

print("✅ CSV actualizado correctamente")