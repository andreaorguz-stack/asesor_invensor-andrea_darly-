import datetime
import json
import numpy as np
import pandas as pd
import yfinance as yf

# Lista de 8 acciones verificadas de la Bolsa de Valores de Colombia (BVC)
ACCIONES = [
    {"ticker": "ECOPETROL.CB", "nombre": "Ecopetrol", "nemotecnico": "ECOPETROL", "sector": "Petróleo y gas"},
    {"ticker": "PFDAVIVN.CB", "nombre": "Banco Davivienda", "nemotecnico": "PFDAVIVN", "sector": "Financiero"},
    {"ticker": "BCOLOMBIA.CB", "nombre": "Bancolombia", "nemotecnico": "BCOLOMBIA", "sector": "Financiero"},
    {"ticker": "ISA.CB", "nombre": "Interconexión Eléctrica", "nemotecnico": "ISA", "sector": "Servicios públicos"},
    {"ticker": "GEB.CB", "nombre": "Grupo Energía Bogotá", "nemotecnico": "GEB", "sector": "Servicios públicos"},
    {"ticker": "GRUPOAVAL.CB", "nombre": "Grupo Aval", "nemotecnico": "GRUPOAVAL", "sector": "Financiero"},
    {"ticker": "NUTRESA.CB", "nombre": "Grupo Nutresa", "nemotecnico": "NUTRESA", "sector": "Alimentos y bebidas"},
    {"ticker": "CEMARGOS.CB", "nombre": "Cementos Argos", "nemotecnico": "CEMARGOS", "sector": "Construcción"},
]

def main():
    acciones_procesadas = []
    errores = []

    print("Iniciando descarga de datos bursátiles...")

    for item in ACCIONES:
        ticker_str = item["ticker"]
        try:
            tk = yf.Ticker(ticker_str)
            hist = tk.history(period="3y", auto_adjust=False)

            if hist.empty or len(hist) < 10:
                raise ValueError("Historial vacío o insuficiente")

            # Último precio e información básica
            ultimo_row = hist.iloc[-1]
            precio = float(ultimo_row["Close"])
            fecha_str = hist.index[-1].strftime("%Y-%m-%d")

            # Variación diaria del último cierre
            close_ant = float(hist["Close"].iloc[-2])
            variacion_dia_pct = ((precio / close_ant) - 1) * 100

            # Rentabilidad 1 año con Adj Close
            one_year_ago = hist.index[-1] - pd.DateOffset(years=1)
            hist_1a = hist[hist.index >= one_year_ago]
            adj_close_actual = float(hist["Adj Close"].iloc[-1])
            adj_close_1a = float(hist_1a["Adj Close"].iloc[0])
            rent_1a_pct = ((adj_close_actual / adj_close_1a) - 1) * 100

            # Rentabilidad promedio anual 3 años
            adj_close_inicio = float(hist["Adj Close"].iloc[0])
            dias_totales = (hist.index[-1] - hist.index[0]).days
            anios_transcurridos = dias_totales / 365.25
            rent_anual_3a_pct = (((adj_close_actual / adj_close_inicio) ** (1 / anios_transcurridos)) - 1) * 100

            # Volatilidad anualizada (Rendimientos logarítmicos de Adj Close último año)
            ret_log = np.log(hist_1a["Adj Close"] / hist_1a["Adj Close"].shift(1)).dropna()
            volatilidad_anual_pct = float(ret_log.std() * np.sqrt(252)) * 100

            # Caída máxima en 1 año (Max Drawdown)
            rolling_max = hist_1a["Adj Close"].cummax()
            drawdown = (hist_1a["Adj Close"] - rolling_max) / rolling_max
            caida_maxima_1a_pct = float(drawdown.min()) * 100

            # Dividendo Rendimiento (últimos 365 días)
            div_1a = float(hist_1a["Dividends"].sum())
            dividendo_rend_pct = (div_1a / precio) * 100 if precio > 0 else 0.0

            # Histórico mensual últimos 3 años (último cierre por mes)
            hist_monthly = hist["Close"].resample("ME").last()
            historico_list = [
                {"mes": idx.strftime("%Y-%m"), "cierre": round(float(val), 2)}
                for idx, val in hist_monthly.items() if not np.isnan(val)
            ]

            acciones_procesadas.append({
                "ticker": ticker_str,
                "nombre": item["nombre"],
                "nemotecnico": item["nemotecnico"],
                "sector": item["sector"],
                "moneda": "COP",
                "precio": round(precio, 2),
                "fecha": fecha_str,
                "variacion_dia_pct": round(variacion_dia_pct, 2),
                "rent_1a_pct": round(rent_1a_pct, 2),
                "rent_anual_3a_pct": round(rent_anual_3a_pct, 2),
                "volatilidad_anual_pct": round(volatilidad_anual_pct, 2),
                "caida_maxima_1a_pct": round(caida_maxima_1a_pct, 2),
                "dividendo_rend_pct": round(dividendo_rend_pct, 2),
                "historico": historico_list
            })

            print(f"✔ Procesada con éxito: {item['nombre']} ({ticker_str})")

        except Exception as e:
            print(f"✖ Error procesando {ticker_str}: {e}")
            errores.append({"ticker": ticker_str, "motivo": str(e)})

    # TRM (Dólar / COP)
    trm_data = {"valor": None, "fecha": None}
    try:
        trm_tk = yf.Ticker("USDCOP=X")
        trm_hist = trm_tk.history(period="5d")
        if not trm_hist.empty:
            trm_data["valor"] = round(float(trm_hist["Close"].iloc[-1]), 2)
            trm_data["fecha"] = trm_hist.index[-1].strftime("%Y-%m-%d")
            print("✔ TRM descargada con éxito.")
    except Exception as e:
        print(f"⚠️ No se pudo descargar la TRM: {e}")

    # Evaluación final e impresión del archivo
    if len(acciones_procesadas) == 0:
        print("❌ TODAS las acciones fallaron. No se sobrescribirá datos.json.")
        return

    json_salida = {
        "actualizado": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fuente": "Yahoo Finance (yfinance); rentabilidades con precio ajustado por dividendos",
        "trm": trm_data,
        "acciones": acciones_procesadas,
        "errores": errores
    }

    with open("datos.json", "w", encoding="utf-8") as f:
        json.dump(json_salida, f, ensure_ascii=False, indent=2)

    print("\n================ RESUMEN DE EJECUCIÓN ================")
    print(f"Acciones actualizadas correctamente: {len(acciones_procesadas)}")
    print(f"Acciones con fallos/errores: {len(errores)}")
    print("Archivo datos.json guardado satisfactoriamente.")

if __name__ == "__main__":
    main()