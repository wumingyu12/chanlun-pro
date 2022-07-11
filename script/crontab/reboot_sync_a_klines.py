#:  -*- coding: utf-8 -*-
import time

from tqdm.auto import tqdm

from chanlun.exchange.exchange_baostock import ExchangeBaostock
from chanlun.exchange.exchange_db import ExchangeDB

"""
同步股票数据到数据库中
"""

db_ex = ExchangeDB('a')
line_ex = ExchangeBaostock()

# 获取所有 A 股股票
stocks = line_ex.all_stocks()

# run_codes = [s['code'] for s in stocks]
# random.shuffle(run_codes)  # 打乱，可以多进程运行

# 只下载自己回测的股票标的
run_codes = ["SH.600519", "SH.601398", "SH.601939", "SH.601288", "SZ.002594", "SH.600036", "SH.601857", "SH.601988",
             "SH.601628", "SH.601318", "SZ.000858", "SH.601088", "SH.600900", "SH.600028", "SH.601012", "SH.601658",
             "SZ.000333", "SH.601166", "SH.601888", "SH.603288", "SZ.300760", "SH.601633", "SH.600809", "SH.601328",
             "SH.688981", "SH.601728", "SZ.000568", "SZ.002415", "SZ.300059", "SH.600030", "SH.603259", "SZ.002714",
             "SH.600309", "SZ.000001", "SZ.002304", "SH.600438", "SZ.002352", "SH.600690", "SH.600887", "SH.601899",
             "SH.601816", "SZ.002812", "SH.601998", "SH.600000", "SH.601319", "SZ.002475", "SH.601668", "SZ.300015",
             "SH.601601", "SH.601066", "SZ.002142", "SH.601919", "SH.600276", "SH.601995", "SZ.000002", "SH.600104",
             "SH.600436", "SZ.300014", "SZ.000651", "SZ.002460", "SH.600048", "SH.601138", "SH.601225", "SH.600406",
             "SZ.300124", "SH.601238", "SH.600585", "SH.600905", "SZ.002459", "SH.600188", "SZ.002466", "SH.601818",
             "SZ.000625", "SH.600016", "SZ.300122", "SZ.000792", "SZ.002493", "SH.600346", "SH.600031", "SZ.002129",
             "SH.601390", "SZ.000725", "SH.601111", "SH.601766", "SH.688599", "SH.601800", "SZ.000776", "SH.603799",
             "SZ.300274", "SZ.300498", "SZ.002371", "SZ.003816", "SH.603501", "SH.600019", "SH.600018", "SH.601211",
             "SH.603260", "SH.603392", "SH.601688", "SH.600600", "SH.601898", "SH.600111", "SH.600837", "SH.600999",
             "SH.601985", "SH.603993", "SH.600025", "SZ.300896", "SZ.000596", "SZ.002709", "SH.603659", "SH.600010",
             "SH.600893", "SH.601669", "SZ.000063", "SZ.002271", "SH.600760", "SH.600029", "SH.600011", "SH.601127",
             "SH.600660", "SZ.002241", "SZ.002049", "SZ.300759", "SH.600196", "SZ.000301", "SZ.000338", "SH.601009",
             "SH.600050", "SH.600703", "SH.600989", "SZ.300450", "SZ.000166", "SZ.000877", "SH.601186", "SZ.000538",
             "SH.603806", "SZ.000708", "SZ.002179", "SH.601336", "SH.600089", "SZ.000895", "SZ.002311", "SH.601868",
             "SH.601881", "SH.601006", "SZ.001979", "SZ.002230", "SH.600919", "SH.600009", "SH.601169", "SH.600115",
             "SH.601229", "SZ.300957", "SZ.002736", "SZ.002027", "SZ.300347", "SH.603195", "SH.688111", "SZ.002050",
             "SZ.300979", "SH.600958", "SH.601865", "SH.600745", "SH.603986", "SZ.002920", "SH.600150", "SH.688187",
             "SZ.300316", "SZ.000661", "SH.601989", "SH.600845", "SH.603833", "SH.600547", "SZ.000768", "SH.600926",
             "SH.601600", "SH.601877", "SH.600741", "SH.600015", "SZ.300919", "SH.601689", "SZ.002074", "SH.600886",
             "SZ.300142", "SH.601788", "SH.600522", "SZ.300763", "SH.688396", "SH.601100", "SZ.002821", "SZ.000963",
             "SZ.002180", "SH.600085", "SH.688012", "SH.688036", "SZ.000733", "SH.688180", "SZ.300769", "SZ.000876",
             "SH.601618", "SH.601916", "SZ.002001", "SH.600233", "SH.600588", "SZ.002410", "SZ.300782", "SH.600176",
             "SH.601607", "SZ.300628", "SH.600795", "SZ.002938", "SH.600570", "SH.601615", "SH.600460", "SH.688363",
             "SH.601808", "SH.600702", "SH.688008", "SH.600132", "SH.603290", "SH.603486", "SH.601727", "SH.600256",
             "SH.601825", "SZ.000100", "SZ.300413", "SZ.002648", "SH.601018", "SH.603369", "SH.600426", "SH.688126",
             "SZ.300661", "SH.600884", "SZ.000617", "SH.605117", "SH.600362", "SH.600754", "SZ.002202", "SZ.000799",
             "SH.688005", "SH.601360", "SH.605499", "SZ.300496", "SZ.300207", "SH.601838", "SZ.002756", "SH.601117",
             "SH.601155", "SH.601901", "SH.600383", "SZ.000786", "SH.600918", "SH.600096", "SZ.000938", "SH.600956",
             "SH.600803", "SH.603185", "SZ.000723", "SH.600875", "SH.600674", "SZ.300033", "SZ.000408", "SZ.000157",
             "SH.600332", "SH.600763", "SZ.002240", "SH.600039", "SH.688385", "SZ.000983", "SZ.002841", "SH.688185",
             "SH.601799", "SZ.000039", "SH.603198", "SH.603606", "SZ.002236", "SZ.002916", "SZ.002601", "SH.688009",
             "SZ.003022", "SZ.300073", "SH.600606", "SH.601021", "SZ.002013", "SH.601377", "SZ.300595", "SH.600236",
             "SZ.002555", "SZ.300601", "SZ.300390", "SH.603899", "SH.601872", "SZ.000069", "SZ.300223", "SZ.001965",
             "SZ.002120", "SH.600026", "SZ.002080", "SZ.002032", "SH.603816", "SH.601991", "SH.600141", "SH.601216",
             "SH.600765", "SZ.000999", "SH.601077", "SZ.002340", "SH.600584", "SH.688122", "SH.603613", "SH.688063",
             "SH.600885", "SH.603688", "SH.601236", "SH.603737", "SZ.000800", "SH.603345", "SH.603605", "SH.601878",
             "SZ.002176", "SZ.300454", "SH.603127", "SH.688169", "SZ.002414", "SH.600486", "SH.600377", "SH.600563",
             "SH.688536", "SZ.002945", "SH.603456", "SZ.000425", "SZ.002603", "SZ.300363", "SH.600779", "SH.600663",
             "SH.605358", "SH.600298", "SH.600219", "SH.600061", "SH.601880", "SH.603568", "SH.603019", "SH.601699",
             "SZ.002384", "SH.601866", "SZ.002056", "SZ.002850", "SZ.300529", "SZ.002252", "SZ.002007", "SH.600862",
             "SH.601966", "SZ.002192", "SZ.000703", "SH.600183", "SZ.300861", "SZ.002064", "SH.600499", "SZ.000519",
             "SH.600027", "SZ.300012", "SH.688099", "SH.601696", "SH.601233", "SH.688777", "SZ.002353", "SH.603939",
             "SZ.000959", "SH.600801", "SH.600372", "SZ.300037", "SZ.000977", "SZ.000738", "SH.600392", "SH.601108",
             "SZ.002625", "SH.600399", "SZ.002738", "SH.688116", "SH.601933", "SH.601058", "SH.603707", "SH.601298",
             "SZ.002607", "SZ.000009", "SZ.300285", "SZ.002497", "SH.600295", "SZ.300373", "SZ.300144", "SH.600871",
             "SH.603882", "SH.600489", "SZ.300568", "SZ.300146", "SZ.002602", "SZ.002372", "SH.600487", "SH.600153",
             "SH.603596", "SZ.000932", "SH.600160", "SH.603077", "SH.600688", "SH.600655", "SZ.000066", "SZ.300850",
             "SH.601555", "SZ.000807", "SZ.000987", "SZ.000630", "SZ.002791", "SZ.002600", "SZ.000830", "SH.603893",
             "SH.600985", "SH.600848", "SZ.002405", "SH.688390", "SZ.002008", "SH.600109", "SZ.002268", "SZ.300832",
             "SH.601456", "SH.600873", "SZ.000883", "SH.600378", "SZ.000683", "SH.603589", "SZ.300003", "SH.600161",
             "SH.600352", "SZ.000783", "SH.688707", "SH.688690", "SZ.301029", "SZ.002407", "SH.601636", "SZ.000155",
             "SH.688301", "SZ.002385", "SZ.002025", "SZ.002078", "SZ.000513", "SH.603267", "SZ.002508", "SZ.002153",
             "SH.600521", "SZ.002531", "SZ.002939", "SZ.000825", "SH.603868", "SH.601577", "SZ.300776", "SH.601990",
             "SH.600705", "SH.603885", "SH.601156", "SH.600549", "SZ.000629", "SZ.002430", "SZ.000831", "SH.603026",
             "SZ.000898", "SZ.002532", "SH.603517", "SH.688006", "SH.600348", "SH.601231", "SH.600177", "SZ.002463",
             "SZ.002294", "SZ.002185", "SZ.300748", "SZ.000027", "SH.600808", "SZ.300699", "SZ.002673", "SH.688778",
             "SH.688188", "SZ.002507", "SH.600906", "SH.601666", "SH.601992", "SH.603529", "SH.603233", "SZ.002568",
             "SH.600004", "SZ.000937", "SZ.002312", "SH.601198", "SZ.001872", "SH.600415", "SH.601598", "SZ.300432",
             "SZ.000933", "SH.600516", "SZ.002739", "SZ.002326", "SZ.000553", "SZ.000401", "SZ.000785", "SZ.300682",
             "SH.603786", "SH.601958", "SZ.300676", "SH.600642", "SH.601168", "SH.601162", "SZ.000762", "SZ.002557",
             "SZ.002422", "SZ.300118", "SH.600038", "SH.601963", "SH.688516", "SH.603444", "SZ.002028", "SH.600859",
             "SZ.000728", "SZ.000960", "SH.600338", "SZ.000975", "SH.688202", "SH.600673", "SH.603658", "SZ.002624",
             "SZ.300866", "SZ.300438", "SH.600170", "SH.603160", "SZ.002223", "SH.600369", "SH.600021", "SZ.300888",
             "SH.600988", "SH.603218", "SZ.000887", "SH.600079", "SH.600968", "SH.600598", "SH.600258", "SZ.002015",
             "SH.600483", "SZ.002245", "SH.603087", "SZ.002831", "SZ.000893", "SH.600566", "SZ.300726", "SH.600704",
             "SZ.002128", "SZ.002409", "SH.600536", "SH.600299", "SZ.002797", "SZ.300604", "SH.601001", "SZ.000729",
             "SH.600456", "SZ.300251", "SZ.300558", "SH.600559", "SH.603236", "SH.601158", "SZ.000958", "SZ.300357",
             "SH.600315", "SZ.002399", "SZ.002266", "SH.600350", "SH.605111", "SH.600596", "SZ.300803", "SZ.000591",
             "SZ.000537", "SH.600872", "SH.603489", "SZ.003035", "SH.600143", "SH.688598", "SZ.002030", "SH.603338",
             "SH.603712", "SZ.002506", "SZ.300308", "SZ.002906", "SH.600637", "SZ.000050", "SZ.002572", "SH.600863",
             "SZ.000709", "SZ.000739", "SH.688521", "SH.600118", "SH.601016", "SZ.002299", "SH.601828", "SH.600685",
             "SZ.300775", "SH.600208", "SZ.002244", "SH.600062", "SZ.000423", "SH.600056", "SZ.002487", "SZ.000012",
             "SZ.000988", "SH.600380", "SZ.000818", "SZ.002472", "SH.600827", "SH.688139", "SZ.002145", "SH.600398",
             "SZ.002152", "SZ.300395", "SH.601869", "SZ.002408", "SH.600998", "SH.600739", "SH.600416", "SH.603858",
             "SZ.002541", "SH.603876", "SZ.002203", "SH.601717", "SZ.002505", "SH.603565", "SH.600711", "SH.600095",
             "SZ.300821", "SZ.002984", "SZ.002936", "SZ.002597", "SH.600882", "SZ.000902", "SH.688798", "SZ.002966",
             "SZ.000998", "SZ.002444", "SH.688298", "SH.601677", "SH.688200", "SH.688696", "SH.600297", "SH.600316",
             "SH.603228", "SZ.300035", "SH.603906", "SZ.300777", "SH.603713", "SH.600008", "SZ.002024", "SH.600699",
             "SH.600909", "SZ.000636", "SH.603678", "SH.601997", "SH.600970", "SH.688388", "SH.600612", "SZ.002465",
             "SZ.002138", "SZ.301035", "SH.688499", "SZ.002948", "SZ.000400", "SH.603025", "SH.600548", "SH.601952",
             "SZ.002044", "SH.601099", "SH.600582", "SH.600867", "SZ.002500", "SZ.002092", "SH.600271", "SZ.000559",
             "SH.601139", "SH.603866", "SH.600511", "SH.600248", "SZ.300034", "SH.600110", "SZ.300171", "SH.601128",
             "SZ.000750", "SZ.000875", "SZ.002926", "SZ.000869", "SZ.301071", "SZ.000935", "SH.600328", "SH.600066",
             "SZ.002439", "SH.603305", "SZ.000581", "SZ.002985", "SH.603098", "SZ.002065", "SZ.002157", "SH.603883",
             "SH.600895", "SZ.002585", "SH.600282", "SZ.002643", "SZ.002484", "SH.600116", "SZ.002156", "SZ.000878",
             "SZ.002683", "SH.601375", "SZ.000860", "SZ.002456", "SZ.000547", "SZ.300244", "SZ.000778", "SZ.300383",
             "SH.600199", "SH.600562", "SZ.300725", "SZ.300487", "SH.600820", "SH.600580", "SH.603650", "SZ.300253",
             "SZ.000756", "SZ.002041", "SZ.300054", "SH.603129", "SH.600329", "SH.603317", "SZ.002690", "SZ.300418",
             "SZ.300001", "SH.600500", "SZ.002389", "SH.688680", "SZ.002670", "SH.600764", "SH.688556", "SZ.002091",
             "SH.600916", "SZ.300393", "SZ.002958", "SZ.000422", "SH.601928", "SZ.002183", "SH.603599", "SH.600123",
             "SZ.002610", "SH.600583", "SH.600057", "SZ.300679", "SH.688002", "SH.600395", "SZ.000688", "SH.600641",
             "SZ.002558", "SZ.300343", "SZ.000970", "SZ.300627", "SZ.002595", "SZ.002747", "SZ.000810", "SZ.300482",
             "SH.688289", "SZ.002705", "SZ.301050", "SZ.000021", "SZ.002461", "SZ.300618", "SZ.001914", "SZ.002518",
             "SZ.300457", "SH.601222", "SZ.300088", "SZ.000627", "SZ.300070", "SH.603733", "SH.601908", "SZ.002402",
             "SZ.002429", "SZ.002617", "SZ.000927", "SZ.000032", "SZ.002468", "SH.600657", "SZ.000921", "SH.603612",
             "SZ.002258", "SZ.002010", "SZ.000930", "SZ.000623", "SZ.002019", "SZ.000402", "SH.600755", "SZ.300294",
             "SZ.300638", "SZ.000657", "SH.603363", "SH.601098", "SH.601965", "SH.603919", "SH.601005", "SH.688366",
             "SH.603063", "SH.600597", "SH.600498", "SZ.000429", "SZ.000966", "SH.603638", "SZ.300623", "SZ.002653",
             "SH.603225", "SZ.002901", "SZ.300761", "SZ.300755", "SZ.300613", "SZ.002706", "SZ.300296", "SH.600131",
             "SH.600777", "SH.603279", "SZ.000060", "SH.600060", "SH.600323", "SZ.002925", "SH.600529", "SZ.002216",
             "SZ.300327", "SH.600876", "SH.600409", "SZ.000488", "SH.688208", "SZ.000031", "SH.600167", "SZ.002895",
             "SZ.300058", "SH.688198", "SH.688029", "SH.600151", "SH.600782", "SH.600507", "SZ.002151", "SZ.000686",
             "SZ.002436", "SZ.002539", "SH.688017", "SH.601369", "SH.600933", "SZ.002511", "SZ.002544", "SH.601326",
             "SZ.002273", "SZ.300476", "SZ.002291", "SH.600171", "SH.688559", "SH.601567", "SZ.300741", "SZ.300677",
             "SH.600206", "SZ.300136", "SZ.002867", "SH.603348", "SH.600273", "SZ.002036", "SH.603179", "SZ.300593",
             "SZ.002423", "SZ.000951", "SH.601187", "SZ.300747", "SZ.002563", "SH.688333", "SZ.300409", "SH.601333",
             "SZ.002318", "SZ.300973", "SH.603027", "SH.601000", "SH.688019", "SZ.002250", "SZ.002865", "SH.600648",
             "SH.605123", "SH.600667", "SZ.000967", "SZ.000656", "SZ.300298", "SH.600639", "SH.605376", "SZ.002249",
             "SZ.000498", "SZ.000016", "SZ.000598", "SZ.002324", "SH.600967", "SZ.002110", "SZ.002182", "SH.600325",
             "SZ.300773", "SZ.002139", "SH.600155", "SH.600388", "SH.603005", "SH.688568", "SH.600740", "SZ.000403",
             "SZ.300024", "SH.600556", "SZ.002373", "SZ.002155", "SZ.002242", "SZ.000550", "SZ.300953", "SZ.000156",
             "SH.601137", "SH.603915", "SZ.002626", "SZ.300257", "SZ.000672", "SZ.300630", "SH.600621", "SZ.000567",
             "SH.688131", "SH.603938", "SH.603355", "SZ.002335", "SH.688776", "SH.688016", "SZ.300666", "SZ.002745",
             "SH.688800", "SH.600007", "SZ.002221", "SH.603588", "SZ.300767", "SZ.300671", "SH.600197", "SH.603997",
             "SH.601702", "SZ.002226", "SZ.300737", "SZ.002191", "SH.688066", "SZ.002545", "SH.600746", "SZ.301080",
             "SZ.002453", "SZ.000582", "SZ.002832", "SH.603008", "SH.605369", "SZ.300339", "SZ.002287", "SH.603927",
             "SZ.002960", "SH.603032", "SH.603056", "SH.603583", "SZ.000089", "SH.603229", "SZ.002498", "SH.601311",
             "SZ.300672", "SH.600776", "SH.601019", "SZ.002773", "SH.688639", "SZ.300068", "SZ.002081", "SH.688408",
             "SZ.002048", "SZ.000415", "SZ.002701", "SZ.002262", "SH.688356", "SH.600064", "SZ.000997", "SZ.000712",
             "SH.603693", "SZ.000035", "SZ.002124", "SZ.000049", "SZ.000540", "SZ.002727", "SH.600313", "SZ.000990",
             "SH.603730", "SH.603297", "SH.600835", "SZ.002243", "SZ.002390", "SZ.002100", "SZ.002131", "SH.600373",
             "SZ.300855", "SZ.300633", "SH.603515", "SZ.002396", "SH.603477", "SH.601126", "SZ.002146", "SH.600172",
             "SZ.002127", "SH.603043", "SZ.002085", "SH.600216", "SZ.300017", "SZ.300182", "SH.603128", "SH.603298",
             "SZ.002810", "SZ.300443", "SZ.003031", "SH.600195", "SH.603985", "SZ.000062", "SZ.300696", "SH.600682",
             "SZ.000028", "SZ.300502", "SZ.300841", "SZ.002851", "SZ.002195", "SZ.300459", "SH.688037", "SH.601038",
             "SZ.002645", "SH.600567", "SZ.000528", "SH.688700", "SH.601678", "SH.600888", "SZ.000546", "SZ.000563",
             "SZ.002171", "SZ.000090", "SZ.002434", "SH.600376", "SZ.002317", "SZ.300456", "SZ.300463", "SH.601208",
             "SH.600330", "SH.600340", "SZ.300224", "SH.600305", "SH.601107", "SH.600787", "SH.600185", "SH.603505",
             "SH.600366", "SZ.000426", "SH.603690", "SZ.002517", "SH.600012", "SZ.300115", "SH.600577", "SZ.002534",
             "SZ.000829", "SZ.300398", "SZ.300887", "SH.603000", "SZ.002212", "SZ.300573", "SZ.002061", "SZ.300203",
             "SZ.002281", "SZ.000767", "SZ.002002", "SZ.002201", "SH.603666", "SZ.300567", "SZ.300685", "SZ.300260",
             "SZ.002320", "SZ.300587", "SZ.002698", "SH.603197", "SZ.000961", "SZ.002726", "SZ.300212", "SZ.300451",
             "SH.601827", "SZ.002163", "SH.600811", "SH.603979", "SZ.300185", "SH.603995", "SZ.002011", "SZ.000088",
             "SH.600120", "SZ.002567", "SH.688383", "SZ.300101", "SZ.002793", "SH.605099", "SH.603396", "SZ.002158",
             "SZ.300233", "SH.603308", "SZ.002416", "SH.603055", "SZ.300080", "SZ.002824", "SZ.300087", "SH.600502",
             "SZ.002612", "SZ.002099", "SH.601200", "SZ.002068", "SH.688518", "SZ.002254", "SZ.300869", "SZ.002237",
             "SZ.000736", "SZ.000420", "SH.600728", "SZ.000685", "SZ.000555", "SZ.002928", "SZ.300072", "SZ.002368",
             "SH.688007", "SH.601101", "SZ.300394", "SH.688533", "SH.603989", "SH.600823", "SZ.002239", "SZ.002839",
             "SH.688023", "SH.688100", "SH.605168", "SH.600869", "SZ.300168", "SZ.002815", "SH.601811", "SH.600586",
             "SZ.002424", "SZ.002556", "SZ.300166", "SZ.002859", "SH.601882", "SZ.300337", "SZ.002314", "SZ.002004",
             "SH.600459", "SZ.300358", "SH.600400", "SH.600452", "SH.688148", "SZ.002837", "SH.688088", "SH.688711",
             "SZ.002075", "SZ.002481", "SZ.002703", "SZ.002293", "SH.601330", "SZ.002946", "SZ.002932", "SZ.002233",
             "SH.600850", "SZ.002635", "SZ.000030", "SZ.000828", "SH.601003", "SZ.000061", "SZ.002088", "SZ.300596",
             "SZ.002967", "SH.688269", "SZ.000718", "SZ.300655", "SH.688665", "SZ.002847", "SZ.000727", "SH.688033",
             "SZ.300406", "SH.600491", "SZ.002190", "SZ.000572", "SZ.000078", "SH.600201", "SZ.002038", "SZ.002135",
             "SZ.002051", "SZ.002126", "SH.600210", "SH.600966", "SH.603766", "SZ.300712", "SH.600363", "SH.688166",
             "SH.600252", "SZ.300653", "SH.688339", "SZ.003012", "SZ.300077", "SZ.000034", "SZ.002537", "SZ.002549",
             "SZ.002913", "SZ.000681"]

# run_codes = ['SH.600313']

print('Run code num: ', len(run_codes))

# 创建表
db_ex.create_tables(run_codes)

# 周期历史k线开始时间
f_start_datetime = {
    'm': '1990-01-01',
    'w': '1990-01-01',
    'd': '2000-01-01',
    '30m': '2015-01-01',
    '5m': '2015-01-01',
}


def sync_code(_code):
    try:
        for f in ['m', 'w', 'd', '30m', '5m']:
            time.sleep(1)
            while True:
                last_dt = db_ex.query_last_datetime(_code, f)
                # tqdm.write('%s - %s last dt %s' % (_code, f, last_dt))
                if last_dt is None:
                    klines = line_ex.klines(_code, f, start_date=f_start_datetime[f], args={'fq': 'hfq'})
                    if len(klines) == 0:
                        klines = line_ex.klines(_code, f, args={'fq': 'hfq'})
                else:
                    klines = line_ex.klines(_code, f, start_date=last_dt, args={'fq': 'hfq'})

                tqdm.write('Run code %s frequency %s klines len %s' % (_code, f, len(klines)))
                db_ex.insert_klines(_code, f, klines)
                if len(klines) <= 100:
                    break
    except Exception as e:
        tqdm.write('执行 %s 同步K线异常 %s' % (_code, str(e)))
        time.sleep(10)


for code in tqdm(run_codes):
    sync_code(code)

print('Done')
