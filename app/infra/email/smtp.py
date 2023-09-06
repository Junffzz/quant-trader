import smtplib
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class NotifyEmail:
    def __init__(self):
        pass

    def build_good_price_html(self, bonds_yield: float, quotes: list):
        total = 0
        good_price_table = ""
        for i, row in enumerate(quotes):
            if len(row)==0:
                continue
            if len(row["good_pe_items"]) == 0:
                continue

            num = i + 1
            good_price_table += '<tr class="xtr-' + str(num) + '"><td class="xtd-1-1 confluenceTd" style="border:1px solid rgb(193,199,208); padding:7px 10px; vertical-align:top; min-width:8px"><span>' + str(row['code']) + '</span></td><td class="xtd-1-1 confluenceTd" style="border:1px solid rgb(193,199,208); padding:7px 10px; vertical-align:top; min-width:20px"><span >' + row['name'] + '</span></td><td class="xtd-1-1 confluenceTd" style="border:1px solid rgb(193,199,208); padding:7px 10px; vertical-align:top; min-width:8px"><span>' + str(row['ttm_dividend']) + '</span></td><td class="xtd-1-1 confluenceTd" style="border:1px solid rgb(193,199,208); padding:7px 10px; vertical-align:top; min-width:8px"><span>' + str(row['ttm_pe']) + '</span></td><td class="xtd-1-1 confluenceTd" style="border:1px solid rgb(193,199,208); padding:7px 10px; vertical-align:top; min-width:20px"><span>' + \
                                str(row['good_pe_items'][
                                    0]['good_pe']) + '</span></td><td class="xtd-1-1 confluenceTd" style="border:1px solid rgb(193,199,208); padding:7px 10px; vertical-align:top; min-width:8px"><span style="color:#FF9933">' + str(row['current_price']) + '元</span></td><td class="xtd-1-1 confluenceTd" style="border:1px solid rgb(193,199,208); padding:7px 10px; vertical-align:top; min-width:8px"><span class="" style="color:#339966">' + \
                                str(row['good_pe_items'][0]['good_price']) + '元</span></td></td><td class="xtd-1-1 confluenceTd" style="border:1px solid rgb(193,199,208); padding:7px 10px; vertical-align:top; min-width:8px"><span class="" style="color:#339966">' + \
                                str(row['good_pe_items'][0]['premium_ratio']) + '%</span></td></tr>'
            total = total + 1

        goodPricePeStr = str(bonds_yield * 100) + "%"
        html = '<div><p style="margin: 0;"><span style="color: rgb(23, 43, 77); font-size: 20px; letter-spacing: ' \
               '-0.16px;">A股好价格检测工具v0.1</span></p><div id="isForwardContent"><div><div class=""><p class="" ' \
               'style="margin:10px 0px 0px; padding:0px; color:rgb(23,43,77); font-size:14px; orphans:2; widows:2; ' \
               'background-color:rgb(255,255,255)"><br /></p><h3 id="id-中国十年期国债收益率" class="" style="margin:10px 0px ' \
               '0px; padding:0px; font-size:16px; line-height:1.5; letter-spacing:-0.006em; color:rgb(23,43,' \
               '77); orphans:2; widows:2; background-color:rgb(255,255,255)"><span class="" ' \
               'style="letter-spacing:-0.006em">中国十年期国债收益率：<span style="color:#0066CC;">' + goodPricePeStr + \
               '</span></span></h3><h4 id="id-好价格计算结果" class="" style="margin:10px 0px 0px; padding:0px; ' \
               'font-size:14px; line-height:1.42857; letter-spacing:-0.003em; color:rgb(23,43,77); orphans:2; widows:2; ' \
               'background-color:rgb(255,255,255)"><span class="" style="letter-spacing:-0.006em">好价格计算结果共' + str(total) + '条</span></h4><div class="table-wrap" style="margin:10px 0px 0px; padding:0px; overflow-x:auto; ' \
                     'color:rgb(23,43,77); font-size:14px; orphans:2; widows:2; background-color:rgb(255,255,' \
                     '255)"><table class="wrapped confluenceTable stickyTableHeaders tablesorter-default ' \
                     'relative-table tablesorter ntes_not_fresh_table" style="border-collapse:collapse; margin:0px; ' \
                     'overflow-x:auto; width:458.479px; padding:0px"><thead class="tableFloatingHeaderOriginal" ' \
                     'style="position:static; margin-top:0px; left:325px; z-index:3; width:457px; top:130px"><tr ' \
                     'class="xtr-0 tablesorter-headerRow"><th class="sortableHeader tablesorter-headerUnSorted ' \
                     'xtd-0-0 confluenceTh tablesorter-header" tabindex="0" scope="col" style="border:1px solid rgb(' \
                     '193,199,208); padding:7px 15px 7px 10px; vertical-align:top; min-width:8px; ' \
                     'background-color:rgb(244,245,247); color:rgb(23,43,77); max-width:none"><div ' \
                     'class="tablesorter-header-inner" style="margin:0px; padding:0px">代码</div></th><th ' \
                     'class="tablesorter-header sortableHeader tablesorter-headerUnSorted confluenceTh xtd-0-1" ' \
                     'tabindex="0" scope="col" style="border:1px solid rgb(193,199,208); padding:7px 15px 7px 10px; ' \
                     'vertical-align:top; min-width:60px; background-color:rgb(244,245,247); color:rgb(23,43,' \
                     '77); max-width:none"><div class="tablesorter-header-inner" style="margin:0px; padding:0px"><div ' \
                     'class="" style="margin:0.2px 0px 0px; padding:0px">股票简称</div></div></th><th ' \
                     'class="sortableHeader xtd-0-2 tablesorter-headerUnSorted confluenceTh tablesorter-header" ' \
                     'tabindex="0" scope="col" style="border:1px solid rgb(193,199,208); padding:7px 15px 7px 10px; ' \
                     'vertical-align:top; min-width:8px; background-color:rgb(244,245,247); color:rgb(23,43,' \
                     '77); max-width:none"><div class="tablesorter-header-inner" style="margin:0px; padding:0px"><div ' \
                     'class="" style="margin:0.2px 0px 0px; padding:0px">股息</div></div></th><th class="sortableHeader ' \
                     'tablesorter-headerUnSorted xtd-0-3 confluenceTh tablesorter-header" tabindex="0" scope="col" ' \
                     'style="border:1px solid rgb(193,199,208); padding:7px 15px 7px 10px; vertical-align:top; ' \
                     'min-width:50px; background-color:rgb(244,245,247); color:rgb(23,43,77); max-width:none"><div ' \
                     'class="tablesorter-header-inner" style="margin:0px; padding:0px"><div class="" ' \
                     'style="margin:0.2px 0px 0px; padding:0px">市盈率<span ' \
                     'style="font-size:12px;">TTM</span></div></div></th><th class="sortableHeader ' \
                     'tablesorter-headerUnSorted xtd-0-3 confluenceTh tablesorter-header" tabindex="0" scope="col" ' \
                     'style="border:1px solid rgb(193,199,208); padding:7px 15px 7px 10px; vertical-align:top; ' \
                     'min-width:50px; background-color:rgb(244,245,247); color:rgb(23,43,77); max-width:none"><div ' \
                     'class="tablesorter-header-inner" style="margin:0px; padding:0px"><div class="" ' \
                     'style="margin:0.2px 0px 0px; padding:0px">市盈率(好)</div></div></th><th class="sortableHeader ' \
                     'tablesorter-headerUnSorted xtd-0-3 confluenceTh tablesorter-header" tabindex="0" scope="col" ' \
                     'style="border:1px solid rgb(193,199,208); padding:7px 15px 7px 10px; vertical-align:top; ' \
                     'min-width:60px; background-color:rgb(244,245,247); color:rgb(23,43,77); max-width:none"><div ' \
                     'class="tablesorter-header-inner" style="margin:0px; padding:0px"><div class="" ' \
                     'style="margin:0.2px 0px 0px; padding:0px">当前股价</div></div></th><th class="sortableHeader ' \
                     'tablesorter-headerUnSorted xtd-0-3 confluenceTh tablesorter-header" tabindex="0" scope="col" ' \
                     'style="border:1px solid rgb(193,199,208); padding:7px 15px 7px 10px; vertical-align:top; ' \
                     'min-width:60px; background-color:rgb(244,245,247); color:rgb(23,43,77); max-width:none"><div ' \
                     'class="tablesorter-header-inner" style="margin:0px; padding:0px"><div class="" ' \
                     'style="margin:0.2px 0px 0px; padding:0px">好价格</div></div></th><th class="sortableHeader ' \
                     'tablesorter-headerUnSorted xtd-0-3 confluenceTh tablesorter-header" tabindex="0" scope="col" ' \
                     'style="border:1px solid rgb(193,199,208); padding:7px 15px 7px 10px; vertical-align:top; ' \
                     'min-width:60px; background-color:rgb(244,245,247); color:rgb(23,43,77); max-width:none"><div ' \
                     'class="tablesorter-header-inner" style="margin:0px; padding:0px"><div class="" ' \
                     'style="margin:0.2px 0px 0px; padding:0px">溢价率</div></div></th></tr></thead><colgroup ' \
                     'class=""><col class="" style="width:36.6562px" /><col class="" style="width:204.844px" /><col ' \
                     'class="" style="width:117.073px" /><col class="" style="width:98.9062px" /></colgroup><tbody ' \
                     'class="">' + good_price_table + '</tbody></table></div><div class=""><h4 ' \
                                                      'id="id-报警数据统计2022W40-P1报警(夜间)" class="" style="margin:20px 0px ' \
                                                      '0px; padding:0px; font-size:14px; line-height:1.42857; ' \
                                                      'letter-spacing:-0.003em; color:rgb(23,43,77); orphans:2; ' \
                                                      'widows:2; background-color:rgb(255,255,255)">意见反馈qq: ' \
                                                      '981248356</h4><div class=""><div class="table-wrap" ' \
                                                      'style="margin:10px 0px 0px; padding:0px; overflow-x:auto; ' \
                                                      'color:rgb(23,43,77); font-size:14px; orphans:2; widows:2; ' \
                                                      'background-color:rgb(255,255,255)"><div class="table-wrap" ' \
                                                      'style="margin:10px 0px 0px; padding:0px; overflow-x:auto"><div ' \
                                                      'class="" ' \
                                                      'style="font-size:12px"></div></div></div></div></div></div><div class=""></div></div></div><br /></div> '
        return html

    def send_email_html(self, sender: str, subject: str, html: str, receiver: list):
        # 定义相关数据,请更换自己的真实数据
        smtp_server = 'smtp.163.com'
        sender = sender

        username = 'zjf2616@163.com'
        password = 'QYMOSAPLMKRCGXQI'

        msg = MIMEMultipart()
        boby = html
        mail_body = MIMEText(boby, _subtype='html', _charset='utf-8')
        msg['Subject'] = Header(subject, 'utf-8')
        msg['From'] = sender
        # receiver可设置多个，数组
        toclause = receiver
        msg['To'] = ",".join(toclause)
        msg.attach(mail_body)
        # 登陆并发送邮件
        try:
            smtp = smtplib.SMTP()
            # 打开调试模式
            # smtp.set_debuglevel(1)
            smtp.connect(smtp_server)
            smtp.login(username, password)
            smtp.sendmail(sender, toclause, msg.as_string())
        except:
            print("邮件发送失败！！")
        else:
            print("邮件发送成功")
        finally:
            smtp.quit()
