# Linux web, search, crawl, and weather dependency review

## Scope and result

This review covers 57 exact Python distributions from the frozen Linux CPython 3.13.5 x86_64 candidate graph. PyPI release metadata artifact digests were recorded for each sdist and selected wheel; wheel RECORD validation had no failures. Static source-to-wheel comparison matched 2,289 Python files, found no differing pairs, and left 2 source files ambiguous because they are native/extension package layouts. The selected package set includes network clients and crawlers whose network behavior is caller-triggered by the service features. Source/build metadata and instruction-like files were inspected as untrusted data; no package install, import, build hook, browser request, or crawler request was executed. The wheel set includes two native-extension packages and no `.pth` startup files.

**Historical graph disposition:** this review's 57-pin lock contained `pyasn1==0.6.4`, `scrapy==2.14.2`, and `twisted==25.5.0`. Those findings and the replacement analysis below describe that earlier candidate only; they are not the current V3 graph.

**V3 Scrapy advisory follow-up (2026-11-02):** V3 selects `scrapy==2.17.0`. OSV returns `PYSEC-2017-83`; its ecosystem range has an `introduced: 0.7` event and no fixed event. The record's explicit version list ending at 2.13.3 does not establish that 2.17.0 is unaffected. Inspection of the exact selected wheel found that `http11.py` buffers response chunks in memory before checking `DOWNLOAD_MAXSIZE`; Scrapy's default is 1 GiB. AIRunner's crawler does not configure `FilesPipeline` or `FILES_STORE`, so the finding's S3 storage path is disabled, but oversized response memory use remained relevant. The crawler now sets `DOWNLOAD_MAXSIZE` to 16 MiB, which also caps decompressed response bodies. A focused configuration regression passed (1 test). This is a service-scoped mitigation; the upstream advisory range remains open. Exact wheel-member hashes, source findings and limits are recorded in the ignored `scrapy-2.17.0-pysec-2017-83-triage.json` receipt.

## Advisory findings

Exact OSV query results for the frozen 57-pin set flagged:

- `pyasn1==0.6.4`: GHSA-2qm8-x737-gmw5, GHSA-9m75-vc3g-4x39, GHSA-fm9c-5rcf-2q5p, GHSA-mm57-4v3p-rchx.
- `scrapy==2.14.2`: GHSA-76g3-c3x4-crvx, GHSA-h7wm-ph43-c39p, PYSEC-2017-83, PYSEC-2026-3918.
- `twisted==25.5.0`: GHSA-2qrf-pqgx-qh9v, GHSA-3476-c5c2-fr73, GHSA-53xc-49m8-p798, GHSA-8pqf-f4m5-798g, GHSA-cwm5-jh59-mwxr, GHSA-grgv-6hw6-v9g4, GHSA-jj36-9pvh-vj5r, GHSA-q7qq-6mhp-9rc4, GHSA-vpp8-g58w-m8mp, PYSEC-2026-160, PYSEC-2026-4304.

The replacement artifacts were checked independently. OSV exact-version queries for `pyasn1==0.6.5` and `Twisted==26.10.0` returned no matches. `Scrapy==2.17.0` returned `PYSEC-2017-83`; its open ecosystem range is described in the V3 follow-up above. These queries are advisory evidence, not a source-safety guarantee. No active requirements, constraints, or lock files were changed in this historical review.

## Source and wheel evidence

All 57 selected source archives and wheels were statically examined. The artifact hash table below binds the review to the exact files. License files and other provenance should be packaged with the service through its existing notice mechanism; two missing selected-wheel notices were closed with hash-bound source supplements: Open-Meteo SDK 1.28.0 and PyDispatcher 2.0.7. Their supplement manifests bind the exact source/wheel hashes and notice bytes. Open-Meteo’s source package metadata identifies the MIT license and repository; the license text comes from the exact upstream tag revision. PyDispatcher’s exact sdist carries the BSD 3-Clause text, while its selected wheel omits it.

No native code was imported or executed. The static review does not validate the service behavior, remote endpoints, service credentials, installed system libraries, runtime isolation, or the fixed replacements until they are selected by a new graph.

| Pin | sdist SHA-256 | selected wheel SHA-256 | wheel RECORD |
|---|---|---|---:|
| `aiohappyeyeballs==2.7.1` | `065665c041c42a5938ed220bdcd7230f22527fbec085e1853d2402c8a3615d9d` | `9243213661e29250eb41368e5daa826fc017156c3b8a11440826b2e3ed376472` | 10 |
| `aiohttp==3.14.4` | `831fc5bd39ec2517851e348f613ddb5447a47cf4b71cb09845af7ad7ed45d8f9` | `5c6758ba62aea282c537179cfc8474a90f2b5f7b089cc5ff66d8920d86a9bfdd` | 69 |
| `aiosignal==1.4.0` | `f47eecd9468083c2029cc99945502cb7708b082c232f9aca65da147157b251c7` | `053243f8b92b990551949e63930a839ff0cf0b0ebbe0597b0f3fb19e1a0fe82e` | 7 |
| `automat==25.4.16` | `0017591a5477066e90d26b0e696ddc143baafd87b588cfac8100bc6be9634de0` | `04e9bce696a8d5671ee698005af6e5a9fa15354140a87f4870744604dcdd3ba1` | 22 |
| `babel==2.18.0` | `b80b99a14bd085fcacfa15c9165f651fbb3406e66cc603abf11c5750937c992d` | `e2b422b277c2b9a9630c1d7903c2a00d0830c409c59ac8cae9081c92f1aeba35` | 1119 |
| `cattrs==26.2.1` | `679132bfdc225c5ee40c024fc42519954767c387f950dc6751946c586bccdc6d` | `a12aaa3453dc8f633a815293179f08b7421ed18d2575c459c3c736f840beac24` | 56 |
| `constantly==23.10.4` | `aa92b70a33e2ac0bb33cd745eb61776594dc48764b06c35e0efd050b7f1c7cbd` | `3fd9b4d1c3dc1ec9757f3c52aef7e53ad9323dbe39f51dfd4c43853b68dfa3f9` | 10 |
| `courlan==1.4.0` | `fbbac7b7fcde2195ea08e707609503c81cf39c891e8d26cdb1fed4585782d63d` | `ad1dbdefd912ca7238d4607dc855df5df097f56bac175dd662c84eed3802f49e` | 18 |
| `cssselect==1.5.0` | `3cbe82dd7acbee9ba9e5723b5f9e4749826912f1fb31cd7f92aabed5fde15b15` | `1d1aded98e82bdde447ded990a191fd6916177c4f0c914fb62eccd58e2ffcdcc` | 9 |
| `dateparser==1.1.8` | `86b8b7517efcc558f085a142cdb7620f0921543fcabdb538c8a4c4001d8178e3` | `070b29b5bbf4b1ec2cd51c96ea040dc68a614de703910a91ad1abba18f9f379f` | 256 |
| `ddgs==9.16.0` | `161ca8e78ea08d40cd3f83fb12279b49322ffb342d981368bfa39bed9847d874` | `175d9198c958a263f51a06a54368ba0b41294942c0cd29f4aa71be03dbcd5f4a` | 37 |
| `flatbuffers==25.9.23` | `676f9fa62750bb50cf531b42a0a2a118ad8f7f797a511eda12881c016f093b12` | `255538574d6cb6d0a79a17ec8bc0d30985913b87513a01cce8bcdb6b4c44d0e2` | 15 |
| `frozenlist==1.8.0` | `3ede829ed8d842f6cd48fc7081d7a41001a56f1f38603f9d49bf3020d59a31ad` | `0c18a16eab41e82c295618a77502e17b195883241c563b00f0aa5106fc4eaa0d` | 9 |
| `google-api-core==2.42.0` | `82cf5daa2ef1b456d4e29ff1de1a5c2995c7be3ccf4fc608184326e03390c1ee` | `b1bdf4f72dc4f910736ce4ba49038352effbbc309579215107649b22973a1317` | 77 |
| `google-api-python-client==2.201.0` | `d5691982abd7287f53cb0b0e0c6a9984d4103cf864ea0a88cb6e4347bbaf70de` | `2d9bf1ba3f12eee8ed3d0f1791ce0605d163432f496baa72d3677faa2cf097d6` | 627 |
| `google-auth==2.61.0` | `37f0815967322e8c32b12bf422531e8b637cafdaae0acbb9141117cfe6a96f23` | `ca60266a37475ae68b63bac007272f46094b3d571abe92aded329b6cfb568025` | 85 |
| `google-auth-httplib2==0.4.4` | `b931de392c20cfaa351cd789274922bd8cdc001e0e9e96de31b39d71347f8e16` | `bbe5d7b2401bb3a4017f4720e1e91bd273ab9a2bb60b84e65edbc0de127852da` | 6 |
| `googleapis-common-protos==1.75.5` | `c7a866fc34ed29a3b10af627a4b9b1dc2433313ca6e959f0ae4feb132047ed72` | `d7285525c23039db98f2463e6d5a4f9b958b94d497f03a844ece3259c4e72d5d` | 199 |
| `htmldate==1.10.0` | `a38df10772ab5d7dbb11896e3f6a852a8491fb1b0965465bc174e23fc2baae58` | `9211dae35ab94147c8ed9e5fc2c9287a5cf31d2394cb7857e7f5dd814eb2aad6` | 15 |
| `httplib2==0.32.0` | `48a0ef30a42db65d8f3399045e1d09ab0ba66e3b9efc360d07f80ea55d286025` | `dc6705cacdf3fb0a2aba7629fa33c90fd93e30035db0c157325826be177e4816` | 12 |
| `hyperlink==21.0.0` | `427af957daa58bc909471c6c40f74c5450fa123dd093fc53efd2e91d2705a56b` | `e6b14c37ecb73e89c77d78cdb4c2cc8f3fb59a885c5b3f819ff4ed80f25af1b4` | 20 |
| `incremental==24.11.0` | `87d3480dbb083c1d736222511a8cf380012a8176c2456d01ef483242abbbcf8c` | `a34450716b1c4341fe6676a0598e88a39e04189f4dce5dc96f656e040baa10b3` | 14 |
| `itemadapter==0.13.1` | `fa139c7be2aa80f8874b2f23d165d5d4aa47c4b85c54ab530b567fd5f684f1b4` | `f3c6b1babb4fb6cca4aa9061ef0b0c25c783c24a571c30e3667e7bcfea41815b` | 10 |
| `itemloaders==1.5.0` | `e6feec5e44e92e1931dbd70fce4da430491ee4cbc9a93a725351e4f0d614a411` | `d57a4e5b204a1f88affdc6e03ed2f4f60ad7f3b7cc90f5914af92c9b52e46efb` | 9 |
| `jmespath==1.1.0` | `472c87d80f36026ae83c6ddd0f1d05d4e510134ed462851fd5f754c8c3cbb88d` | `a5663118de4908c91729bea0acadca56526eb2698e83de10cd116ae0f4e97c64` | 14 |
| `justext==3.0.2` | `13496a450c44c4cd5b5a75a5efcd9996066d2a189794ea99a49949685a0beb05` | `62b1c562b15c3c6265e121cc070874243a443bfd53060e869393f09d6b6cc9a7` | 111 |
| `multidict==6.9.1` | `0f06e60fa190aa7abd0914c2a766736fdc8e9f34878c4346338534b73d1b20e2` | `7bf6478188f4e47bf5686e8a33da4ae28bf43b1b2528d9ee144d28492bfac60b` | 10 |
| `openmeteo-requests==1.4.0` | `bb8e70ca4606b6225c69911e81ce2886a5635c9a96bea7525701f42070a27811` | `05514b2795b03dd2b1964cb98136bf793702eb39dbaa2fc9a61cab58c808312d` | 6 |
| `openmeteo-sdk==1.28.0` | `e77011b34f8696eb8cd6756d22b6868f9b3420671b93285171f2ab0ea3be1ba4` | `e975faffd9f3095ec2e10409b1233913b5110a2cf47dd7e64fc650c661619fe2` | 22 |
| `opentelemetry-api==1.45.1` | `aa38ed19bcc084ba42782a73255b3582283eced7ad6dddbd6695189e69adfb75` | `b31553efa588ae44bc306f863c785c5333a9ecc091248c6ee68b4b6c87fdedfb` | 47 |
| `parsel==1.12.1` | `f526df846f3a91e13f5499156ea3e755114834cd126b62cd1d784ef558f3a713` | `cf74e09857329bddc02c13ae239a9b46f410dc5bd1d05361c8c2643a1a5a7149` | 10 |
| `primp==2.0.1` | `82ba17b077bef19a189d9ec8d77ca632496cb444e0f4fa37e27e90041cf0da8f` | `9a7be373adfded677a9092ae2743873d5c8a9573148d617a189d26715f7d8ea5` | 8 |
| `propcache==0.5.4` | `ff6b113f50bc066a698db5d944d2c6dc7507168dd3341e255a8892fd0715a558` | `62c60aec739ed00124573cce1178138fd690c7676352d67a37328c1cf51d7468` | 12 |
| `protego==0.7.0` | `2c032d9736a1f4f0c4318f3558353ae34da5cd038f1a5e064ded7548df315e5a` | `944638aaee608f6c83fcad442695f3f9381a60be8d5007248f46b00f201fa5fc` | 10 |
| `proto-plus==1.29.0` | `cfb4e62ad7e13dd18f346cabbda00cab39930d36a05791fd81ddb074d6ee884f` | `8acd070469a7aaf43f440b022ef9757c8cac1a9f866e933f59ae98669ddc6c8b` | 31 |
| `protobuf==7.36.2` | `497d0463ff3316681da6c0b9e8d06cb465d61abce00b613ab42226175644d1bb` | `bdb3a345d48db958e6ce1f18e508beb0cc981d64f24088427549c866cd039f1e` | 62 |
| `pyasn1==0.6.4` | `9c447d8431c947fe4c8febc4ed9e760bc29011a5b01e5c74b67025bd9fb8ce81` | `deda9277cfd454080ec40b207fb6df82206a3a2688735233cdcd8d3d565f088b` | 38 |
| `pyasn1-modules==0.4.2` | `677091de870a80aae844b1ca6134f54652fa2c8c5a52aa396440ac3106e941e6` | `29253a9207ce32b64c3ac6600edc75368f98473906e8fd1043bd6b5b1de2c14a` | 138 |
| `pydispatcher==2.0.7` | `b777c6ad080dc1bad74a4c29d6a46914fa6701ac70f94b0d66fbcfde62f5be31` | `96543bea04115ffde08f851e1d45cacbfd1ee866ac42127d9b476dc5aefa7de0` | 10 |
| `pyopenssl==26.4.0` | `28dfcce0162b9211413e26dfbfdf1d24317fbeba18fc93c12400a1856b2a0bc7` | `f0eb0cb2d581d3ad2b9c489468485e7f2ab6727d08401bcf9d824c3caddf3c1c` | 13 |
| `pytz==2026.5` | `fa23724b9c486543b9ff54a327ee7569ac83ade54bb9afd0fc18676620401c86` | `e658af3757f9e26a9d25dd2aff38335acd92bc9104f890a894b2c1ba28311b03` | 616 |
| `queuelib==1.10.0` | `063c821c32859ae8bdce2cc9e74156645c074218a464f8262e29a3b8de839737` | `257936b7202d12325c80ad79e254c59e2cd3533704ae6dffb567b1a0b309ae5e` | 13 |
| `requests-cache==1.2.1` | `68abc986fdc5b8d0911318fbb5f7c80eebcd4d01bfacc6685ecf8876052511d1` | `1285151cddf5331067baa82598afe2d47c7495a1334bfe7a7d329b43e9fd3603` | 32 |
| `requests-file==3.0.1` | `f14243d7796c588f3521bd423c5dea2ee4cc730e54a3cac9574d78aca1272576` | `d0f5eb94353986d998f80ac63c7f146a307728be051d4d1cd390dbdb59c10fa2` | 7 |
| `retry-requests==2.0.0` | `3d02135e5aafedf09240414182fc7389c5d2b4de0252daba0054c9d6a27e7639` | `38e8e3f55051e7b7915c1768884269097865a5da2ea87d5dcafd6ba9498c363f` | 6 |
| `scrapy==2.14.2` | `23bf5d37503ad16973bd09604b9c36249bd4bbc282c48ddedbf58105d4639337` | `dc6ddf6e1601fc6c50191d2e4d4a65497e37c4b848f542f21c9278a55f86af42` | 192 |
| `service-identity==24.2.0` | `b8683ba13f0d39c6cd5d625d2c5f65421d6d707b013b375c355751557cbe8e09` | `6b047fbd8a84fd0bb0d55ebce4031e400562b9196e1e0d3e0fe2b8a59f6d4a85` | 10 |
| `tld==0.13.2` | `d983fa92b9d717400742fca844e29d5e18271079c7bcfabf66d01b39b4a14345` | `9b8fdbdb880e7ba65b216a4937f2c94c49a7226723783d5838fc958ac76f4e0c` | 28 |
| `tldextract==5.4.0` | `6c9223212c15c25c0da2bf7313893c14f175cb36b64a0c42da67a468e0c61ee3` | `7f02aed30bd3b6ad5717192eb859a39b20aafc7caf3917d9cf6cb00a58efb34f` | 16 |
| `trafilatura==2.0.0` | `ceb7094a6ecc97e72fea73c7dba36714c5c5b577b6470e4520dca893706d6247` | `77eb5d1e993747f6f20938e1de2d840020719735690c840b9a1024803a4cd51d` | 30 |
| `twisted==25.5.0` | `1deb272358cb6be1e3e8fc6f9c8b36f78eb0fa7c2233d2dbe11ec6fee04ea316` | `8559f654d01a54a8c3efe66d533d43f383531ebf8d81d9f9ab4769d91ca15df7` | 888 |
| `tzlocal==5.4.4` | `8dbb8660838688a7b6ba4fed31d18dedf842afb4d47ca050d6d891c2c15f3be4` | `aae09f0126a8a86fa736be266eb4a471380d26a0de3bc14844e7821fee3e2a15` | 11 |
| `uritemplate==4.2.0` | `480c2ed180878955863323eea31b0ede668795de182617fef9c6ca09e6ec9d0e` | `962201ba1c4edcab02e60f9a0d3821e82dfc5d2d6662a21abd533879bdb8a686` | 11 |
| `url-normalize==3.0.1` | `1655cd214159d9d47dc37aa6ce993c2149da44fa35cac6bafd90036a4eda3ac3` | `97ea68fc543b1fc9f270f34c90cf164453e7d490da2ec653dcd8ebd4e3ac1faf` | 23 |
| `w3lib==2.5.0` | `a7ddf714508ddc1b8563bd19ace2feb28080bbaca39326cbc964359f6754f615` | `136fd5edfe64b53b8579838e2a7e803495bbbe6b69ddfaeed3c29a794b44f6ba` | 15 |
| `yarl==1.25.1` | `03dd38de09bc213e9a8b29761eec33ee1d5318dac0e49d8af36e4d27830e23a7` | `681c758b0490f9e96b78e5fa8e8dc6e648e9185bb6eaebe73183c33ea0c445f3` | 16 |
| `zope-interface==8.6` | `b40ef9b4873afb5d0dec02b8d2dfde1cf18c72337b60c99cb735961e0bac05c0` | `09522cdc6a77376bc36988b531db3b568c8cb0b6ca7286d8316aab283888770f` | 57 |

## Notice supplements

- Open-Meteo SDK 1.28.0: `packaging/licenses/openmeteo-sdk-1.28.0-supplement/source-manifest.json`; exact upstream license at commit `00ac91cf7267e7750b816af3d7c054e75c8f8ddf`, plus source package identity evidence and selected artifact hashes.
- PyDispatcher 2.0.7: `packaging/licenses/pydispatcher-2.0.7-supplement/source-manifest.json`; original BSD notice copied byte-for-byte from the exact sdist member and bound to the sdist and selected wheel hashes.

Both manifests were accepted by the existing `source_notice_supplements.py` loader when checked against the frozen exact-hash lock. The loader check was read-only; no active spec/config was changed.
