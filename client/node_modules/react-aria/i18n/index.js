let {PackageLocalizationProvider, getPackageLocalizationScript} = require('react-aria/private/i18n/server');
let {LocalizedStringDictionary} = require('@internationalized/string');
let {createElement} = require('react');
let zh_TW = require('./zh-TW.js');
let zh_CN = require('./zh-CN.js');
let uk_UA = require('./uk-UA.js');
let tr_TR = require('./tr-TR.js');
let sv_SE = require('./sv-SE.js');
let sr_SP = require('./sr-SP.js');
let sl_SI = require('./sl-SI.js');
let sk_SK = require('./sk-SK.js');
let ru_RU = require('./ru-RU.js');
let ro_RO = require('./ro-RO.js');
let pt_PT = require('./pt-PT.js');
let pt_BR = require('./pt-BR.js');
let pl_PL = require('./pl-PL.js');
let nl_NL = require('./nl-NL.js');
let nb_NO = require('./nb-NO.js');
let lv_LV = require('./lv-LV.js');
let lt_LT = require('./lt-LT.js');
let ko_KR = require('./ko-KR.js');
let ja_JP = require('./ja-JP.js');
let it_IT = require('./it-IT.js');
let hu_HU = require('./hu-HU.js');
let hr_HR = require('./hr-HR.js');
let he_IL = require('./he-IL.js');
let fr_FR = require('./fr-FR.js');
let fi_FI = require('./fi-FI.js');
let et_EE = require('./et-EE.js');
let es_ES = require('./es-ES.js');
let en_US = require('./en-US.js');
let el_GR = require('./el-GR.js');
let de_DE = require('./de-DE.js');
let da_DK = require('./da-DK.js');
let cs_CZ = require('./cs-CZ.js');
let bg_BG = require('./bg-BG.js');
let ar_AE = require('./ar-AE.js');

let dictionary = new LocalizedStringDictionary({
  "zh-TW": zh_TW,
  "zh-CN": zh_CN,
  "uk-UA": uk_UA,
  "tr-TR": tr_TR,
  "sv-SE": sv_SE,
  "sr-SP": sr_SP,
  "sl-SI": sl_SI,
  "sk-SK": sk_SK,
  "ru-RU": ru_RU,
  "ro-RO": ro_RO,
  "pt-PT": pt_PT,
  "pt-BR": pt_BR,
  "pl-PL": pl_PL,
  "nl-NL": nl_NL,
  "nb-NO": nb_NO,
  "lv-LV": lv_LV,
  "lt-LT": lt_LT,
  "ko-KR": ko_KR,
  "ja-JP": ja_JP,
  "it-IT": it_IT,
  "hu-HU": hu_HU,
  "hr-HR": hr_HR,
  "he-IL": he_IL,
  "fr-FR": fr_FR,
  "fi-FI": fi_FI,
  "et-EE": et_EE,
  "es-ES": es_ES,
  "en-US": en_US,
  "el-GR": el_GR,
  "de-DE": de_DE,
  "da-DK": da_DK,
  "cs-CZ": cs_CZ,
  "bg-BG": bg_BG,
  "ar-AE": ar_AE,
});

function LocalizedStringProvider({locale, dictionary: dict = dictionary, nonce}) {
  let strings = dict.getStringsForLocale(locale);
  return createElement(PackageLocalizationProvider, {locale, strings, nonce});
}

function getLocalizationScript(locale, dict = dictionary) {
  let strings = dict.getStringsForLocale(locale);
  return getPackageLocalizationScript(locale, strings);
}

let deps = {};

function createLocalizedStringDictionary(packages) {
  let strings = {};
  let seen = new Set();
  let addPkg = (pkg) => {
    if (seen.has(pkg)) {
      return;
    }
    seen.add(pkg);

    for (let lang in dictionary.strings) {
      strings[lang] ??= {};
      strings[lang][pkg] = dictionary.strings[lang][pkg];
    }

    for (let dep of deps[pkg] || []) {
      addPkg(dep);
    }
  };

  
  for (let pkg of packages) {
    addPkg(pkg);
  }

  return new LocalizedStringDictionary(strings);
}
exports.LocalizedStringProvider = LocalizedStringProvider;
exports.getLocalizationScript = getLocalizationScript;
exports.dictionary = dictionary;
exports.createLocalizedStringDictionary = createLocalizedStringDictionary;
