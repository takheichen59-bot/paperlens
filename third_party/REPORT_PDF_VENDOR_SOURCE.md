# Browser / Node report PDF dependencies

| Asset | Version | Source | SHA256 |
| --- | --- | --- | --- |
| `pdf-lib.esm.min.js` | pdf-lib 1.17.1 | https://unpkg.com/pdf-lib@1.17.1/dist/pdf-lib.esm.min.js | `72c052d97b4d5d9fa6cdbdcb7ad709f03d4ddb1122390cb3afeba4d88651d969` |
| `fontkit.es.min.js` | @pdf-lib/fontkit 1.1.1 | https://unpkg.com/@pdf-lib/fontkit@1.1.1/dist/fontkit.es.min.js | `05a5e5c35bcbd0958dce2ed1a5353045ac04f12ae595f104507b1a924d40d0c4` |
| `pako.esm.mjs` | pako 2.1.0 | https://unpkg.com/pako@2.1.0/dist/pako.esm.mjs | `94d300905740b5f3d1200df0bc79348319d080bce8e6474ed852bda4c22690ee` |

All assets are self-hosted below `website/web_assets/vendor/`. The only
fontkit source change replaces bare `import e from "pako"` with the local
`./pako.esm.mjs` import. The above fontkit hash describes that delivered file.
No CDN request is made while creating a report.

pdf-lib and pako declare MIT; their package license texts are retained in
`PDF_LIB_LICENSE.txt` and `PAKO_LICENSE.txt`. @pdf-lib/fontkit declares MIT in
the exact npm package metadata and its README links to MIT. Its published
1.1.1 tarball and upstream repository do not ship a separate LICENSE file;
that packaging fact and the verifiable declaration are recorded in
`FONTKIT_LICENSE_NOTICE.txt` rather than inventing a copyright holder.

Fontkit WOFF2 decoding was exercised in Node using the existing local UI
WOFF2. Runtime PDF subsetting failed actual raster inspection, so reports
require a static TTF and embed it once, compressed. A CI subset TTF can be
prepared offline; it is distinct from the complete production font. The
production font is the separately pinned OFL font described in
`REPORT_FONT_SOURCE.md`, fetched from a same-origin private asset route.
These libraries generate PDF documents locally; they do not
interpret scientific claims, call a model, or upload paper text.
