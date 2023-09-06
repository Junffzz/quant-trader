import requests
from jsonpath import jsonpath

# 10年国债收益率-中国外贸交易中心 https://www.chinamoney.com.cn/chinese/sddsintigy/
def get_cn_bonds_yield_for10_from_chinamoney():
    headers = {
        "cookie": "apache=bbfde8c184f3e1c6074ffab28a313c87; lss=fd9e664ef34511dcdc4a51a4e8d84abc; _ulta_id.CM-Prod.e9dc=761f906ca092d64f; _ulta_ses.CM-Prod.e9dc=f3245a084d54257b; isLogin=0; AlteonP10=BxMtWyw/F6wn+n8Uny4yTA$$",
        "origin": "https://www.chinamoney.com.cn",
        "sec-ch-ua": '"Chromium";v = "106", "Microsoft Edge";v = "106", "Not;A=Brand";v = "99"',
        "sec-ch-ua-platform": "macOS", "sec-fetch-mode": "cors", "sec-fetch-site": "same-site",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36 Edg/106.0.1370.37"}
    url = "https://www.chinamoney.com.cn/ags/ms/cm-u-bk-currency/SddsIntrRateGovYldHis"

    params = (
        ('lang', 'CN'),
        ('pageNum', '1'),
        ('pageSize', '10'),
    )
    json_response = requests.get(url, headers=headers, params=params).json()
    rows = jsonpath(json_response, '$..records[:]')
    return rows[0].get('tenRate')
