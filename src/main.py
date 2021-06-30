
import yaml
import re
import argparse
import logging


from exceptions import WebDriverNotFound


from decimal import Decimal

from selenium.webdriver.support.ui import WebDriverWait

from selenium.webdriver.opera.options import Options as OperaOptions
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.edge.options import Options as EdgeOptions

from selenium.webdriver import Chrome, Firefox, Opera, Edge

from selenium.webdriver import Remote
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities as DC

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


logger = logging.getLogger(__name__)
logger.setLevel("INFO")

parser = argparse.ArgumentParser(description="Crawler - Projeto Conif")
parser.add_argument("-o", "--opcao",  help="Rodar o crawler localmente ou remoto")
parser.add_argument("-d", "--driver", help="Qual webdriver utilizar")
args = parser.parse_args()

# from selenium.common.exceptions import TimeoutException

URL = 'https://bi.saude.ba.gov.br/transparencia/'
OCUP_LEITOS_PTRN = "(?P<LEITO>.+)\n(?:.+\n(?P<TOTAL>[0-9,.]+)\n)(?:.+\n(?P<OCUPADOS>[0-9,.]+)\n)"


def load_local(config_file, navegador="firefox"):

    logger.info("Carregando o webdriver local")

    webdrivers_obj = {
        "chrome" :   (Chrome, ChromeOptions),
        "opera"  :   (Opera, OperaOptions),
        "firefox":   (Firefox, FirefoxOptions),
        "msedge" :   (Edge, EdgeOptions),
    }

    configs = yaml.load(config_file, Loader=yaml.FullLoader)
    webdriver_path = configs["driver_path"][navegador]

    if webdriver_path:
        wb_obj, wb_opts = webdrivers_obj.get(navegador)
        return wb_obj(executable_path=webdriver_path)
    else:
        raise WebDriverNotFound(f"{navegador} path does not exist. Please fill it in selenium.yaml file")


def load_remote():
    logger.info("Carregando webdriver remoto")
    driver = Remote(
        desired_capabilities=DC.FIREFOX,
        command_executor="http://localhost:4444/wd/hub"
    )
    return driver

def load_driver(conf_fs, args):

    if args.opcao == "local":
        return load_local(conf_fs, args.driver)
    
    return load_remote()

def fetch_selenium(args, arquivo_configuracao=""):

    wait_time = 360
    logger.info("Obtendo os dados...")

    with load_driver(arquivo_configuracao, args) as driver:
        driver.get(URL)
        try:
            # espera até abrir o site
            wait = WebDriverWait(driver, wait_time)
            fr = wait.until(EC.presence_of_element_located((By.ID, 'dashboardContainer')))

            driver.maximize_window()
            driver.switch_to.frame(fr) 
            driver.implicitly_wait(60)
            
            data = driver.find_element_by_xpath('//div/p[contains(., "ÚLTIMA ATUALIZAÇÃO")]')
            assert data is not None and len(data.text) > 0
            data = re.search("([0-9]{2}/[0-9]{2}/[0-9]{4})", data.text).groups()[0]
            

            ocup_leitos = driver.find_element_by_xpath('//table[@class="PageTable"][7]')
            assert ocup_leitos is not None and len(ocup_leitos.text) > 0
            ocup_leitos = re.findall(OCUP_LEITOS_PTRN, ocup_leitos.text)  
            

            ocup_leitos = serializa(ocup_leitos, data)
        
            return ocup_leitos

        except Exception as e:
            print(e)


def serializa(ocup_leitos, data):
    
    assert len(ocup_leitos) == 4
    assert len(data) > 0

    ## Extrai o retorno do crawler em variaveis para legibilidade
    # Enfermaria adulto
    enfm_adulto_total = ocup_leitos[0][1] # Quantidade Pacientes 
    enfm_adulto_atv   = ocup_leitos[0][2] # Leitos utilizados

    # Enfermaria Pediátrica
    enfm_pedtc_total  = ocup_leitos[1][1]
    enfm_pedtc_atv    = ocup_leitos[1][2]

    # Total Enfermaria & Ativo
    total_enfm     = enfm_adulto_total + enfm_pedtc_total
    total_enfm_atv = enfm_adulto_atv + enfm_pedtc_atv

    # UTI adulto
    uti_adulto_total = ocup_leitos[2][1]
    uti_adulto_atv   = ocup_leitos[2][2]

    # UTI pediátrica
    uti_pedtc_total = ocup_leitos[3][1]
    uti_pedtc_atv  = ocup_leitos[3][2]

    # Total UTI & Ativo
    total_uti = uti_adulto_total + uti_pedtc_total
    total_uti_atv = uti_adulto_atv + uti_pedtc_atv

    # Taxa de ocupação
    ocup_enfm = Decimal(total_enfm) / Decimal(total_enfm_atv)
    ocup_uti = Decimal(total_uti) / Decimal(total_uti_atv)

    # Salva em um JSON
    result = dict()

    result["TOTAL_ENFM"] = total_enfm
    result["ATIVO_ENFM"] = total_enfm_atv
        
    result["TOTAL_UTI"] = total_uti
    result["ATIVO_UTI"] = total_uti_atv

    # Objetos da classe Decimal
    result["OCUP_ENFM"] = ocup_enfm
    result["OCUP_UTI"] = ocup_uti

    # Data que os dados foram disponibilizados
    result["DATA"] = data

    return result


def crawl(args):
    
    with open("./src/selenium.yaml", "r") as stream:
        try:
            ocup_leitos = fetch_selenium(args, stream)

            return ocup_leitos

        except yaml.YAMLError as exc:
            print(exec)


def main(option):
    logger.info("Iniciando o crawler")
    return crawl(option)


if __name__ == '__main__':
    print(main(args))