# ui/gradio_ui1.py

import gradio as gr
from recommendation.db_recommendation_engine import run_recommendation
from recommendation.pdf_exporter import export_recommendation_pdf

LOGO_DATA_URI = """data:image/webp;base64,UklGRgIvAABXRUJQVlA4IPYuAADQBwGdASoIAoYBPmEqk0ekIiQjpJBKKIAMCWdu4WqvLSZxvdq/JfuW9/40/7vZnw/+364PMD88/p08z/mu/9f17f3b1AP731PvoUdMT/Y//NlHfqf/bdz3KKzQyYP+V/jOPPgEe199NAF1cusTkAfqx/yOSA/I/932BP5t/gv/B/hPd//z//P55vrH/0e4X+vfpyed57L36s/+0j9O88Ar9TRSaDkxEidVzCmemMjp54BbTBtzwC2mDbmCaCGvHucJuOnfWIUdw1rKSMTM86e7LTX+7UgdvzBtzwC2mDbnfxA3Zognff/QeLuPue9ZMoN+gi46nHQ1skg1eIIHsE7cOiIS1Kvb3RUgLaYNueAW0wav03WLZEb4GnEBJnw81zoGUkYtXxSep9qvAau4LQSTgaTyeAjFR9C6WaCPnceoC8EQAr71SBxueAW0wVy9vzSZvyksypli1q7E3TbAHMjNYrebgIdcW/01NO6JF+tfA16Nhq8jwbEjNbKoMfX53A3NuVzZwsddDRUJhtzwCnzWHO5l0WIDg1vxC/+1NGWuX78Y1JxOCBIFdf9yflaHpehHLHxjeve5C17ZVCaTQdIo8PTD253a1Pl1IQGefb25uUNSknyb/tKO8EaeO3aG6+i8UokfD6ZOmcvp9DwVvk3D0RanuDJN1V6akVdlNciS8bnAAVoH4M62tPuq7KJtS33m9TYePlu2i2opkh1mQ313e9zuUhDaTc5vGBR7QxsFrWlWFs39EZV4uvF4xg7vcrQyPW/UPMtw+nsn8ORhA2stj6BuoJYQUHrkcq+/5UM3NuYuzuR2lpHxN2K0LoN9I5d7pGfxHHD4V0rodROHE7xUs9f1WvqBoJvsg7m0XdxS7uXKuPNwIYdDg2TDLVUutqI75cVYucr73YkBAfDJZ9xZa9VEV4W6DlEms+Otw/7cQcdrAp5flVW8BGS0q6qPLA/XboCDFlm6oGVPqlCu70eLVSyXdqWUGh1T1uFkQXXgyjKcWn05hzlcghJ0pbXiNyl9Lfc0sl593x2z6GiP9Rd4dL7c5sSIqk42fxiJ4HuK2l7+yhWhdUGu9mM2HQfC4LDqNMD1+c8W+C8Ep4B+p3nLKIKgr32fn2OLHI9keQJksZt/jmj160He4Dk36TFHHCOUh+N5wvR13dLUtcWO+a6NKrJyN17jsuoID3flr53W+VfXGuyKy79mHRfCTNwgFc4gnJrW6M5CY73zYmaITFQvDLk/OQTq0dbJ7LOGYmXabscWVfo/Y1IjJzzgm+UESKdKlWXHS3rDn5u7Qux4WaUe9zeDgWqT8Cb9XYpiW/j5qMvhzbhmafJ6fcXFbN9V4PCkjGqt/KLj5hpHh16HUkRntvly2LKnlYInzeQeHSpR8yVHb4nEwDmnf3i3Tnkhqm3A89gFrfInWVG5w9T3ePY2/CyXXNVvEZ39o7AGNdfrVdAkXE9gGkcTF8qMxxQKAqzK/XSWlnNBe118wnf0OiR87QlcAQApapArtKcEX4CP2dM1C/Yib5W09QPLDdQz4W3JQ0U7OI9Knuo9OLPL0szphWbZkbrlJ0dxakUne9hvg48YGtxljapaa90wsfwZ2fXcM2hrKwQKvWpwaWyaGZSXAdIbyW6YyJncS/mZH0l+W7YSV3JM6drU2VxLgbHJgrwtJAWhv4Fw75sI8zE+7B9fHsvJCPyPEsabOHz6RcTwPM1MyCLBRmoprx5ftFqtHhIO2iQa8w+wyooPS13VmYTDtPpv2AflBSZgWNHFetqVRbyMdLKRgyI0geToNtZYvxHvjSsIoUylAT6PeOh8DLW3nzuEvJqqXE1TTeow1OhtcxpB6NaNyGr6k3KqmEMkf3ry5NH6RAVnTcdJ4jFiuNo/QtQuCfhINhX3uTGJ3132bl6tWP0qoOXy/FNAlW40jYmhonCouF0zaEW45FRuZYOX8rFLizNnNeJle70QjXVGA35K9QrgZIiw8nCl0oywnHYb6RFhsQ7+9VSAG3K00iNnicD1jTKfsPPui+/7FP6vy0as+zQXBEyzf/VX61P+KeM0EYA+9USy+c1fTN/3/ub9dvJJ95HkheOSkIHGLLV/HIoMeJOViIeVREo+fQhA1HRc9QGYKcFlCngi9pR6/J3T+oLBW4IihvT/HF6jvFSwXY3nCudEo+BxMRpClvM7B3xcVlY4sXML/zgB7WPuY1hCGbTlKSnZDy5yZjML23N5dUYwV41TJWWnbvAaIH42W6zIzqu8EpnC7bB8rAHvZiRbQG1UbzIHMe8F+d2kHWxexwR0Bv+gZX0mdLX1vkbq9Jeq2E/+hJoU9Nc/ukHnUaZGCCmjL/6iuSU7r7R93dwaJwbMLJBzoX1QU6rEBpeBi80iyY1vp1Gy39o1DGKE2sh4uNdmpLaam20X76xlq6uCjyAYwXWnHczk/Tz3XAqSoDV26enYoapbvlrqu9lATsWKws4FfHuzL+aM+knCgQDBjHyTCvLnAyfZeIP8U1prAlT2SmaIIfjiVE0Hw9RTXcSzP6jsN57Pxb4JMR1s+u+hIhNpjewIslz9SycG9VMTQAVUh9VwA/vjegta67OKQxudcgRY6fFx+hWeDa3tLaT+9b3VYOHpDP7MJCfJH0GtZPgoTQQzBtgda/GniDzaZlZANg03SINELPpUvH/CPdTFdTvV66iWBhZCj3opyIz0BGVM2/NTRZDgVCFcZPeY6rdF/g+nKHf/suD51IAR+3HSmN/w51uC/Pg9x9Zn7QKv2TD+3kmPt97J//Dni0+Y+gGjO/0IZNENj1p1CED21u9QsnFUoa9WNprnHaU/GQRytpzi3YwiQiwAAP7+z5AAkPjiCO/31y1Vz/u+uhkiSv3sKxxsggmq7XYLuqFAAAAAGtOEr5VtmW6gX6/s4pRUslCRaAWR6X4URcRAh5//8WBn/kbAjFgpYxCVp/PxHsLSUtMa1tydDCXHfIS4WQ2dB9rLTxVrOnMmN3kI3IBMdHqLZMDNrEwQ4H1Z6CQoVQXP6BvdGdsLsX3OzdeC+OPrSViFmxQV+6iyaQBBqbPGsgfUoGt+LPdrJX9oKHx4Y2g4Fd3NGE97XwJvFcl1WSpKP3Xj3/0Eww7MKBs2mdzAcK6Ptt0m9U5m4aY2fR2KyE9UPNSVcRV5iLBwn61rfg5JGtLmbZlwqaZefKSKAszRYAAAAEiEA9Bz8VXz6IsRDGIXw9+tAANtBeTsfFovuGu08Te2TfUADD4Z95OZm7+cNPm6rxwMNRpCnSgpebmpkmNflKk93HbWzGT4Tdwd9FVyQpVfE80vNzg/RbMrK+QvGJTyBGt2XrY0c/bvJNhUxKvH+d5GB+R3eDRINLTn6w9oXCF39wKiDFF0OqyBEFJN/YHiIg2qYP0g4QAJ9wovpWA13OAbKKnv0uwY55sHhI1twMzHHqYGlV47rBfaHPf+T32rxPhBbuwt0ZvtM7fUxJ2Z8Vqnhti5slVwt0PK8Dh3TGjidaVg+clb27U7JPAWciKqe9pVJexerL3bcylDDwav2rHJVli74dLFjpWfiXvcV/Xwj60lhL+vFFTWkeAHS3cmNkAAAApgYcBOjbASiEHP1AKbJwCQn0+rQ6yauIH02yvzZfwsfDwZa27FToNQ/kC0Xs/yjVwIkO2uD+J/e0QD15q7YJzsWJSJgOqx9B6YeIGkSmSFX7BMdqa2/+AH5exps20giA+A6NDy4Z0Et5yRdV2/63pnADeB/8/8m6yD/SAmBbmp9MBBlSI2evnBxLdPPvNXidrqGxnam8YQ3GsKDgTBTGRctT7jx038EhyABWURtvEK2NltSSJN4PqSEIrgCNGLz+eIrim7O/O9ybo8anZIUuyklf8JGHrmYERIjGRNQUwRGGSBiElE3xknSiG/gyz8yEH+he+WwWzaYIBEf1JRQIaAzVNblpCOg8gBaXP7tANaYze2eB/A+JQyV0hNW2aZwPNDuYjGzKuGeETfakAABpZPmKuVtsQjS0wL++yCoKicgHd8WMX7LCqV9B9xnc4fa9YNVmZw5miv+O28VnX7PzbnGUrbpXn8fYukcJZWnIPo2fmRDaZvAKMnEGR9htrOkQQ8Mg69fSwxkS37yXqx8xjxN/mdXKIFqlQnnsmdmdobOHM3bzJPkOSoj/LaJBl5O9qMX7JIUXWK4nf4vG127jQD7k7yQOvhri+HM23bnr0ROj1/5ErdYhFBLv+f2dDKM8POKgPscp+dvouhkkA7muhY/mS4fNIbzdgLOK7M3+4Bn4U96RBe9I0+MkZ94766k6ritv9c00s/OfyCnW//9XLrsRjU+k3GTZLqIjzQPG3C/+xKyiMxIb4GGYkRxhPCM6gvSGHlvwAY+rInnZbeZIY2FcF6Iaf8m9ObwXl4nxhXrNGv0xpliyDe2ipEJGhw+BMrH85E5f8h0j5f7OI2D3E5Soolpl/hmwggEO+5Sb54lpk/h9q1ZLZeF0AJUJ9CPTHqxIhFFiJsnFzInL4tZEndmXjK61DGG5qXaZRZ2nT/OAzq0RkKnvLrQRE6SzJL1nEbDx9AeVNBUPuBtcotLJbygTI2aDe3VT9xis9Ib4gfk4rDN1+v/e0q5fjY/CpRyqiE3Z+ybKlj/q7Llg1UQ5n3oKSdsUlk/pZi3st6bPGCCHQwXXRP0HwO+gPYuBgxKN32Bnu9ErgABumbTUQHzG3b4KYkL8KhuX5B+P9bCSGnvY/Rj/S96GhWHmhKclutJhUnW8M9kjzQQXWrQH0p9z+X4NMuHPcf8egJM6r+Rnj7shd1vCb8AAf9RO8Gs8kinT9/VI9CaxehnyGvlllpG7wPa1IhlcAocZqEySDl/d1sa8jS+NV2yJuAmOuEZjZYATAhHigb1RC9tJWzY9/uSSC8mBLLbNB1PZCSUVB4DeL1Ss0KKxhtLfCaaKZ5PSMv3uAZB8cepa4N53D5k+InDn+zt33khtwlCj1GuVj13E7AYlqd91W6HK3vCiNeW8EK8AnidrHyWJuU2ZH8PEAf5z15eiV8Zaq8GR476UInfwSvsHzuoU1R4wUd3T92B6/P58smrl0mFrdUu1DCSZtsYyqW+uyTYTKD02z0Zo94jQ2Obkiz43fk++yV1g9+FaTZeBfcHpzfbgsTml+SrTtat8vTC6svvIGI6uI4ykTG5JT2HGoJoScML3q2rGH4+kygGfrwesaUPNZBsQhSX4jHkCqUOio6FrhKibXPqjvOPDmdYxvHvAX11i5ml71Y6y9YEnPBo67Jlecm0LRhwtBGcTW3X86xtjbzvl9K1nFfWY+PP+bWg4AHpDExpLT0jQAoB5SZ0N9DkIDW6VL48UKXV0lJjZSKZxf4/pGPveSM3NYYYhlo6ekYCfdwZ0esVRRRI3j4siPHncrObT2iSCf64LGlPxLLkVPyIrYIPHpBf0ZEqsscjzTNc8eodB1Xa6QuddtiCkmpVEczPi7XOj1loCGtlMkyQ5uFj9r+XeHhssoSYwZ3TPvXkrQLxD3tpFHTUTEC/1PR9gzZJtarasHxU/pKWcg6pzHIqIJDIOZTn7khPcqg15BSqDp9JfYWF3uNPC9n+9ujEuVImwuQMiJoT+FCGPKqmuZjsZ3qI91sOybQ2kef93S+yVUc6/H+StW+l5+2Ktep76WKPCnT3YoaDHiPHqqVLqNv/m199w19crMse0q65PsuMVhQlLY3n1/VyorXZHxSMoF3k5PCS80Fw/zcrKtb31t/0927Zd1u8urZq4fawJDRx/Cx6wHe3f6ni/JHzu8/0f2f1Hq5SgMqOhiyaHI2ngW75OyQ0S5gF+RSMmLb36kB/KHP4dYjQFC8CnhW5YwdteIRP8S6Olyre1xi8xb23vFhUtAWOF4RQMybs6hppcemuACVsZn4DxthmEL77AAypO4V7YpVOM/pvTZhH8mDj1jYz4FXznVM9bar9YVQbLG6W+AYEmD0szN3QAvhjAuyoqbqdJHzdQcPj+TPgRcCZOj/KQvTrznBE4s+jCtoHJvKU8gbGAwrEQdg8yCR4NCuZJD517pw7uwMBRwchEm8i6pXTTFyAHpcIxKhA3HFtbrFWvEPdplVqdrRpsZt/BGUT7kyoNdDZ5O0nGN35IMfKc+N5+t1A8FEtyKUa7WvZaqCdHEB4fw/llJYRX43TCec/HXcLi5WVWzVpxRsJIdFzfWEhok6OCySTRqhJp6bNc23+u/B1T0gMQVuE6jkIILMP+TNdhpd7H9R8OD1pd2cNYht0U7rXghTy4fYDHjyWfsQRDyvrBa2Z2y3zgb7w6yStFxaPKFRxJMY3XormtMgLNSUua+PcEiclv8ics6MwAE/4gP8PxNb3WS+hq2iDTHGz/PHWD5KEXVuwP5QmD6AAABFvNMQxAA1nRVzO5culfGnFm00m3wMVSwLGdzdcaKZWbtTMVlORyVapjm8ZZ+nmE7I3tqWq5lliLemQTAQQDE5W6jCMJlTOPDxBfK3OU95xVVWekMXme2hgjADonY7Tta4KNyosRGEMi3SHSoAdEAzXFy7sP49DQPsm/fpCFDRyhKarJLACcVtno4SJhkRIWT2OLXrbfTKmwm98iRZAb/yOYd3elh10Viru6lJcZuznanGIvEUq4v6mbYmqJdkTnwj39LXBCNxMW0x8RYPBM15QZJyUNjgr2yeVoTzgsoWYSvUSOAedoXq8wVvlRVSS06l94rbEK1pp1+MH5he5bztTNB4UU1CFL/5u0SEnbwVcMx+rCXnk2jd7VKfYtlANDQRbkJ2/sr/pdgPOfmSxKumn8gY8IcnAYdbvMxcN0dr3dAsLhEDhY+fqCaZ2rrq3mmQraMeTSlcIUeDaBtRW24YfJ9MhWXRLTvJr0nlbkQT4LCWqoBSTpnOp8LbPKycHX8EU/AbtSuehyxu4BTQ8F1K6R9JYag0UbHvBsAWePPb5IjjkyO/ggNRG8TXSJdMiAFxFmIBKcJ1L859lphJbpYGGzK0eIkdX6tbMi+VrZnG/EGDiuAl3VGwg02DlSlr5600iEDxBw35/gJ1zLbGC3Ik5GUpafa6hiuApvomT3IBt2b5fXKyLcOwUzofMQbcG9GPoAafREIuVDmQuJypQm8siNDEyw7GBQfXEquKm3OqlNl2bb3ffWN7eAOl4Z6VzBlo9FWg/TZl+x6u0ARRAMdVL8rXE+nAESJNl6vGqyCT2XTh0X+fnek2snIDrkwJVXpk2mK5sUnF7s6NVrog6XiQoClodchoI9FYCK0J4aGZGJsa+OloWEpxv5D7dDtCXv/G4MWQRRdBS8wL4+n4UvqJhJunhfYgYZDo8FVjkvJVAO/PkaxiQTgyvamlKtFkS+z2Z5UfED6r2KYMY452DHxin8YXgjx4LD7cQnIYEJqjAe7tYaHienUjrpN16Fmr1mreFw1EE5XX9RP+ASD5AItOQif2CoXQhhxZEYzkoMFBskLu0kYzwTVGzNOFpIMmERtiZ1EeGx6dDXN0GP1H2nyDFAgLUiAwWH5t4g68ZNz21iF0wJKpx42O5UXgd5UInJnUckxeoJ6T7f20frREK/NIOtkCyY9XeSSZR0Bt0qny/BLej0JbgmhwevfYTsJQTLhl6LWV2/4FuXQBZK4EJyH7aICSZgz8fcWXpf0Fd1FFALTeIU6KGqKRrEgKMtthH8vkAAX9+yA3WQKci9+2OtcG/HazABJ3cD0mNstGdEkOqqjgCVD+qS/WybA4FQDTMHI5h+dhp4ZEbWeVTITHUucLsa9vsl14YORyaglqoYHhQz6SFsIXxdfuSVtUVYY5wqUzdLQQ4eBEgR1/MIt4hVv8QRP43VW+co2YIQKFL4qJ3OaM1MkKz3B2fW/5pDHWsYuaGKKqIK3l2gyeIqRWwopIaRmRvstp404ykvziAexuybgArPhIVwvAw4/7xMBkQ22iytgtU/Xe9BdCGC9AAQdLyhbI+UKBUD8NUgGG9q2QGJVe0UAEENuqWxqXrYG/wZIQFKqFdRb3QDAPNx/eGh/zPFuNxPuTQMivh1dHaIKwWH/uLSFuvb9GnXzoYPfRVK2D9ZzRB6wABQ2s4W59JgvR8HnHPMoE3uwrBviBFYnskeVrbbm4xA/wDI6YvO8F8qUdIKymF2kpfh1F58Zo8hWADhMs1Bm3QJBV+QwVdA8HAX+cQYAXnyxOWprohaW/ZA8EXkx5+2C+ql46RBD6CRLGBSLB5fR+O7CUOp75EsgxrMJrEFgI1Jeu4PDWGPHNMhHl/G47cy+diW90fJnUBeeGrUbDU8AWMFNtTJo4tgDmc+WaSNIewin2M2tmCPw0PuwklXQehg08zIF0UtlLYzwtBQYHHJy0jiouE56BVqaqaQi8BQG8ivvnam+z3toj9gZs+AQMvqv0+jDpvh6t48BaB1iczB/mJYia7QbHRTyJWGvEA+3bSkSH5w/xusGHwBc4f7O6tpf/cXziNvOOzklcxGZgD12vsHx3w6xpuE3fLIpBCASxQMaCOP8P/1BT6T0AcJ2raBKafAAVk475M5d1CfzLDdudMGsSqLwIPp2ClEwQEz4e+30FTiuhLs9u/zBQ1FmIQC3vCt9yeIRn2bnKgUb4b9oO7HK/ulsuOpS6elixidrkfulbnsfE0Xn8RHy0zIRhvc8V8uYOzEe5vg//IovsGlWe+8n9WxMunpRkA3qjKcFU19LjGF4ZAAI3vSKEXmERTfTNSdxqOw1EnEUKEdzr9Hr92aAAMfVJA1v+ID/fZf67k1w3sUe4yaq0TNHrUTak29PDCnRZ3BAQ2/uZ5GhkKgeE5PZRon7rVqFBhvKJGV4HHa2VN1G6D3gdFHIkYKIHsHkefeTf3eFPba7JJMZIE2yScIFZrjrCnlp/aerpgm2NEwyH3kUPntjUdtjAKq4xZFE1QIA0MHtNpJyq2jcp/Sf1k6o7Gyjbkpez9lYJbKKm0dto1h9ry789rtYR35Y42jZM4/Xt4G4uBIH2WwqTAp+WchdjfLF62abgj87B5n6STXaAE1IspKCVMftmMdvWOy8Xe1FPN3PTi2rDrzgrzXzG5wZeRHgUQevadwlnQporCTREI2e2sYr6qU/T9kNH9QEgRO4TB8W4/g5lhUUHCQPTQSuIxF56266FgabCbm/u1WyQkl6V/CKRyKOmJLEFa6Bf8trxAu2i3to0Pnxubw/Vmk9YgS/1ozYIxwRUPUXqpy2zZLCTX5zL+Ug8apIP6yVuP1ms1dGEgsztW8eWBOsGgOuLQtZu9yrlM8Om+GVHpepjnfKLgpsbTOnWba+a40HMBy4+Ylcmi4vGS9WJkaE820gsLeFBc3YB6JKY33jsUQRH/vE/fTINbjGNJCvfvkU/soe4pB1S4qU1RA0c0YWAYunKf74JSHILWSMSw2o3vfuu6g5h9hN1hNqRQODC3fRVmyh9ZdVReou+8eb/4gLIXgO5420aR6OKk/TsDeU5Ho3XPlC4qiZGoIMQr6+dOZXYaZq9YbPK5oL+O9Y8MY8BhEH6Qr3wS4YPHzXhdEv2k37dQaRZGe/P27/TE2oeJkFy+E1oexcsVLS7OCymicpPB34VNQM65YBb+R4P8ErS8QR1zegvT1KRaKF1QGduDWdtXF5k0Py9JKbzyPv8/niPkCnHJBVdLiNi1CQjmYC5cIIkNXPuU0FaFJjdjnK/mBkQqPouEuFwHj/fuA3gg2WUo6lJdqXP1ws4w96SKYkyEHqdXnUBe7myLJX1eeh7YfJnsok/+Hne18nC1+1ZTgFa4zHbFMTmCv5d6E0JmKNky3ObhVWS0QDV7QdjcLuXDJ0fUfkTFQCqp3eXtoB+bdXJmEnqW10r8RCbsgo58FiBykkkus6zMpDtzQD8CxkT6wGArj4TPkYQZdUIqCVGIJ6CIkv72snOGk62EfZ9GhO7vywU26VNkx3EOWX4/V7B6ZYMYoU70l8swrG/RE3vSuPtQEdY4Q8BpkluV493GNTDPrlDCaUXCAqdN8oyYMj8PL9KXctguGFcdx1NB3uYQJaSCmWmBdxdXt49ZbAXQwQK0XHc3Hyh5BJOZ2jqt1aYEMW74T60whqwHUtzQ/9JQsHWHunz/3P03JhQSS+czpz6Y3Fsw7egJURm4fK2Tvv6Dru9EHXE5DnRc0/o9tjAbdHB8rrv8n1/gH+vcY9RRCk2SAoXQ3+WfyfW+9C3tmOeFmT2wu36pcXhX+lCV+2NssxJSHErYEQWe25rhFqHCSJA0UyiUWQYQSBPK1Jvwsz7IsdvupL0xyfBqU9z15U9H1tnVLUEscT+vC2YAO5c9gcU/DQbK7K/siHkt3sxDGQLrjxmmnnRlfr/UjrnVy+gKNrZ1gIqSqoGecbM9NzXP01WKmZC/YT2Q+wqZwvkhndjzskrCpwE/d9PPm23i40YdF9lpwjsvrIIoAKvBNsEm/HJAKnjmSrJiIZio0zhFPb1Kr6KZGwHWDtaAq+zD8h57tSYhyTUbL+jBpFjb3X/DhuaQZPYK6tb6je11mB79eimr2viDC2E4UAbNlywTQuRmBJq06dSkludwEMKiJJNDy28zuWx5T34lnHIm5KkfsFRtl/rKMi7BevwZW9fNxDAcXEahAghNdI6o9Kq/BKDMGvzT1v3Kfdi/cKgWroiYOYwDiDLaL/0oBSczHNFsno2A6Jm4mMZw0OAFpjHj8kkr+WNL41CmbJIMjdbsJBU0NGdbqCniZD3a88cHPnyoU++jIkRbsFbhs8mWJWJ0Dt0mKhTrfC/QJxfKW/bLL7LKVW4wF5Gy7gbvYPcHaBxAKGRaJ40gLJrmPfxsDfNAmI8Jc4wnQ/7W/0B+ZOQeS1XvIetwZbS5Md7CQTZpHuZMrHTAVIrlNC6HKfgkiH2YWWIa7GGboGU+UlKm/cPshY4hBGGg+q1A/pP17q7Wvymj4f4NnfiZ4EkCXd+yI516XXGyzI/m8ApKvKJiM8y7MDx5IfNliHjOiUeILcpvqT2FwMawnBjcqmE2C5qNU5zkQUOnuTHIcHFiS0+kmJSQKXsRBbq8xZUKFM7gdBKQYEqhoskVTwe62HbNYltL2v/Rt0BMAHL/AsVdw86jUoIDvub55zd509dg/P+XSRjQVrYWOXgseAuR6P/YSWlZNAMGxkrGzNWAEX4/EKVMoX4uKDw4rTCtsuAHzuzDKV0wKRjsk7tbp/49wpw66zwwR/0N8DankDSwhb6au2aQPcbG3VuByqxOB/Pdr7N6E42qNWWEB1FReVr7pLVrV/VrlDcxZ9yE8IQwubw3x2FQkBkZe0Qs6PWBJIddAh04NhK8ivi6phj2M91ryLqgZhwSE6/S2bkubK0HlS+Yg3mM9cVfKDAceX2fdswPwApn3gEwXZLud6jrgsR/PQ2i8D9ldZf/yLO8w25WIzTDUb0gwPKLd6LciTTtI+NIHacfoj1Juf0hp7dAk01OCcPsA+JDxJ8kqwJfJeuTZRoj8Dl1yY1cidz+7TxuiEAS+kuPq0WXB3alil4pXxtHLN8myY7hBb2RQs72vgJQTlN+QN+N/AowQMgrdshHuNAIiu6PY04ABv7+H2Ebso4wI8gWLH/xPUZmmaYK6uq/2BmKDGI8HgzH0E6XfKRDTcRKzmrkaKvvjvyAsEkqOk92vfG+xN9kmAlPlrb4wQHroEvOS857q+a4c2fZTrpdfdkfSHWoxy8fMQRp8Z+S9Zf0xqbAojyiWteG8O3gW7PKO64hgnAxBW9ZUWsGsvw8GWquOoQKIAnM9Q8fZOctp8Ws2Rk0ovlJVo+POFNQ6NF/1QwPzTlt5mo8GNL3HRKaaEiWFERcXUlGcUIc9THSzNGrWbBkdF/UiDONVSoBqj63UTEGajRLz0tkoz0lr5zaQTyVWZABYUb3kuDnPj8ssqNmiJ6J5voRsPToQkr+QT1z3cVmZBXD3CFyJzBchuqx0AQGfx/NbFIMtOwy27/nTsT61+Hr8cKeV6aKbmC6I7Y/C2ETlsj1yNZNMIPuELSvM3cxeZFLAzbUczmOZ5TQKf0NE8n3RuRE5PxTDOjAG2yuOGCDB+Ckqqlk6GLsJ7SiU+z7jqRitnfF4cWJTbnLo/ruvWApGGa4nhJCQAVhnzZ6VSwD2oq+uQ1vI6pQcmgWIwq01dH2omykEEDDcm1F02O4Lke5lqWEhl0KZBYjNVoCv4ggct03VoiFpB2TPDae32cyNntVeB37PJpA94g65XkZ0AcGd6cIfXFMgOeo3/P+S2XmWIuZe3M7Da6JyNREermjbwWpR2tgATyESVbRdFDZAmivliZv599GwVsi5oVoa32tYGtZGEGxr45GtfZgGbHYN0uAvkki9Tu825S1n+6GY0dsgR5oVgYBUh95C89NEd/wEUC7kad7x51bL209+tlPHiSc/Yj1pAUL1szThWNlJl8BXnAhqh2FtW3vY0fZl1FwcOQYZX0ZzCDSzYbQLfez+q+n/SQXGBPwPQ2FuQda8LpyULkXrtrfXaZgZX7Cv7d3VDGRE88tGYfrmpVVDVd6W3IgOxC1BABmVZ8ms5H5ohSuL5s4ZTTcayvL4QOzPE8dGpzt5ChZS5Wuy4aqt4FPNn5zBBUPJeHlpRzP3pJp9RmxgUcL9i0Ht2tcwS+Esv3uvz2ji08vdqsMY9Z3V0S/Dl4lH+RrPFHGXQw2jX5lnTVfPIMRjICd8zKZcl9c3ob+zUrZ+br7cpxb54J8R/8pq1KUmmhYTLaEwl+uTKnPkXCywcJaYqALjwvQqEK8SDGRuO3tuDIy1QLAcKX3yAftmfhmJrBn4GtWS4s2Em24TpEQL43dEdqOgA7g6+PLzFjkXnb8BJVIjpbTYIXjaLQ9gam8O7l7ncLXFlJg41Fz2ctuXi1j+JJAbkY5vDMZCKUe6bUG8s0/wgdAxtgSsZye3Gboq2cHISgadQ9GqzcOrD2nA/EtKTJbBKiqREgOiqLznWU7yv+sY17CDJwPMX/UQih9nSiIY2x8mdpTHxyWd0sVb4zsV+nNxZB1I1Sbm7ZTeKCtL2jXnAGE9NdRNoMxqw7yipDSunffFXYWSrG+cZuvX92bkUkM+puMtzGwpi74DRwyurm6CPUIpVq8FuZP+UG5dSTvH/fevErBo91HK01FkFTEw4NdisbLI9Atu2giy0iHDk8bDIoX/YIL8GiAKEL40tcuBr+OZ+sGOtQt6XypcV+K6Bw8DIGHxMrAIUckFxhPpzWP/GafRDa93SL4Jbre9fdS9CH2LiB34z55SzoKanY7YFHtUKs1ht/UAeGtfqJesbYGpMZk+OJaJbTWiHaTCmJAH/0eokXkygkCGiwcnak2tT+2CdfpTtLEDc8FcJ178bxYFVfcJ2nzLGlsvnRBKS5xl5PLnw+G7fSjH7MeYdafBnyt8HrxWXrKQOmC3t1IuYF1pmK1E7Iy6zfasvacMg7twLtBaQ4ldcziR0v6+Zeno6bUf6C46HBopdDBe9IIy3PGyMSbvvljNXmM6cBWhlnWyaalgf87XfyD4oXGD/mq05JPL6aVYT9o8JHorcbr4BpAgDQrTPdoEqUESe+9+qAiwB8aoeYN4FCsx4g3c0m4yTLCbYvENGqNtebZgC02H0KE5mfxgqfZImyixucvtZs1Pl36+LjUcucG+Ay9lXs/BpktrdGNQAqJAKYJ7J6zUwtKoDBrrJwcY/hK+nWTb6RUvU8yXxm0LnNuKctV1MPHKISCICgit1LjFs+lEF1J7rEg6Vz9iC1fw30RcLJ42zHwXCb0tRreRT+WqzufkZhVJPFUELufFOHwqy6SKc2MUnbD9RhgrPuY7nvf23ymtYqkLOAdOdOJ+HAh+LyQwA/4V2352DZfFCWTajIJEGlBiH/UA85JoVoFq8SZM03b/aNpuc7t9bnahVijAn/oHj7n08nkGzvf0P0fmkw/yrL6mMNbqfJnN4UWPy6J0YeymjlHxSfqBezB6hn96xsp2Qcfy9hXLNbDOGkf+CT3WofyBYv7nXlRf6awIIfwECOGXUbH2+ZBmXNA3pVoj+z1pTOMk2fUWeF090wL2aTw1VnNuQxFb4MLCJkCzwV04+rX1pv6/T2sOJUfgiST5Hxvge7kR5uWmR1+IcUoS90My34PDIdmdKdYnfHjer1J9cBwG+yRShZgV0wJo9ji+YhRc9/JAo4BJqjnttNZgaSepXWcem3YUoa3FI07Dx9lUHuH23W/dVI1lVpOxaaS6XhdylAkg/oOrMk+NJAFDmm75o3dBXTw0+YTV+Exdf1pki6lRBZq/fFZNIyf2RNv5uSUVWhKf//8nFaM8eUsogrDmlpN1Xd6Zg/SY3iTAzDYmvnsy/nkx7XFWtdA86V/oIHkgtfeh5Mh6SqyuTOkxs476kSLQ0wpZgg7N069D5vUkA7HyDxbBXqEmv74rVc+nGIIszImJgNnqi7HJgWPwAiPdTgwotv/aQ68ICzJ+RfxfjiVCLxQKL7tXFH1nNEXE6Rat1WnS5FeWlxEn5Ek9S/7n1DY8O+ohQIjtj/xhETPG1IIxOIe3VGGEiLiuuHqvKvIUHy5Ud902Tt3CpDIetiJM5zKDH01FVxu9M4fHe6sFbIQI+ElMoeXcMjrO6iI5MRF2lz8af18z6xwigrNJD6F9drFDPW0OFdyzdoTFK8Gfsh4NcLUQDls1tqet2di6iU+KZTRZcGdiqpXa1e8SsWoM1zk+u/rLk9eEimulgIOqkOxdyrhjP+/Lxf1YY9nxZmVbeE0vLwUSHTJkl1UGdEjG/6JDmhF2TykWDi9dNZizhbKtmYlDTL7OSs1X5bNAhXHOP+GHUfXRSrxbcvlMIufZ3IaTjwpnvK+FZkETPLQmKir6gpRL36WI/xBvxhC/p0ahEcsIW/T9+4MaroIJuKkia6XAgONpGvoND6GHRIl2+7NnnU+jWSjFxAHH7tUhIqNR/5qH9BljFaVF/L3L140DbnRuTvyqYut7WSYyNgwl58uLUnCWus3f1z0OdEkVVgufZud6vhD5+aINc+5lYB9oMpUjAFw/rsPeJeuSkl6Pl+3uJbSXkWPAWcMxRxX/X6xzt/H6hXzEGvvdRGuqjg7/u4wNtIfWZXIvrj9PA9fYnltCheUBJat9WTxR2m7CgyctYZ1niNK0sLA8UxHUvI3WMIF8pNDD0Wp0UhLv/LrQqLZ2lp1xo3uvuZorrIqJweBggmzo1A2FruQwkqBYbFxgEqKFjnEOyOpqHEn5wnJRo4zTWJmWLaYC0edAANxAZjdxZjfiAN168BdHUd1uLuisK59S+TZ3Lp3mnSy2mVRVEYAvy7wb/yF6BipwzW/VH+S9tmp8LIBuMbpAKPFDrGX2qCSJuvKKDnoFMG0Il+/aG5/psM6rT+SvxwgvfFYeftK2ajj4zGA2Vc/zA5skCmKL27Wj6NmZ1FDlUlqNBR+eXPt1zjyZixWPj4UTgkJD3WPiP6KW+oQCAJEca0hsyw/RTDQ6cVClHnn2cxpdA8lGPwzXKZ9taAK7Q1ppI0G8gLx7CK/OKrJvxQLlh5xxoK9EzyU3BTxWm2HxwipfardLLxr+Sb5tyw0nHLn/oJUZ7/ldHoqTfTfO5gdm5NU7qcvSJliKHvdk2uPqFshnJK+8QYvB3kfASNbLMn/TgqtkCqW4vZgLlLu7QAJ/MpSSiZ8RX1DiI5lMsC0FuuEEOvZ3++LpwRuiXdXw38FyxM6QAN2JtLKgmx5Hzd0ajXDj6iyvn4whW2BNp4BiYNIOxEcVRIgsN2sy3ePHSNxHIAloR7JqIrt3dfNijapm2aw38hwfi73Mo7tWc051fkTq2Z7fiX0j3N4mhViBSUzaBUKW7coOM4B1vmzyBtBNUVLBfGsz0YPOs2kz+p4vKKvKufE9xOpQumOftNWH6FqtSrBXdSjS1VQsTTAyNWXcjVsNaXwy8sHMfQ4AAA2EnIH0aNDMZnSS7roe+n9MzXnz2ZfxHmoouD8pBxbMfW6cNo0Wp5HQkj9orbaE0lAzXNuahw8QdZuIRUN2AbDcMscVkg9IhUzm1C7k/D2gdWnATuwD8yl4kgmSJmI3x7w5gHts1aPtx8TqPEr3h30BoPOkDSG63VVsYgYC79Zmq6o1JiJX939u0Uhy0MCCdQXU9IYDkqgKEeAAAA"""

CSS = """
:root {
    --primary: #6C4EEA;
    --primary-2: #8A63FF;
    --primary-light: #F1ECFF;
    --label-bg: #E9DFFF;
    --label-text: #351A92;
    --bg: #FFFFFF;
    --card: #FFFFFF;
    --sub-card: #FAFAFF;
    --text: #1F1F1F;
    --muted: #666666;
    --border: #E5DAFF;
    --border-soft: #EFE9FF;
    --success: #59B36B;
    --info: #4A90E2;
    --warning: #FF9F2E;
}

html,
body,
main,
.contain,
.gradio-container,
.dark,
.dark body,
.dark main,
.dark .contain,
.dark .gradio-container {
    background: #FFFFFF !important;
    color: var(--text) !important;
    font-family: "Pretendard", "Noto Sans KR", Arial, sans-serif !important;
}

.gradio-container {
    max-width: 1440px !important;
    width: 96% !important;
    margin: auto !important;
    padding: 20px 24px 28px 24px !important;
}

h1, h2, h3, h4, h5, h6,
p, span, label, li, div {
    color: var(--text) !important;
    letter-spacing: -0.02em;
}

p, li, label, span {
    font-size: 14px !important;
    line-height: 1.55 !important;
}

.gradio-container .block,
.gradio-container .form,
.gradio-container .panel,
.gradio-container .wrap,
.gradio-container .gap,
.gradio-container .compact,
.gradio-container .prose,
.gradio-container .gr-box,
.gradio-container .block.padded,
.gradio-container .input-container,
.gradio-container .row,
.gradio-container .column,
.gradio-container .tabs,
.gradio-container .tabitem,
.gradio-container .button-row {
    background: #FFFFFF !important;
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
}

.clean-page,
.clean-row,
.clean-column,
.clean-group,
.clean-page *,
.clean-row *,
.clean-column *,
.clean-group * {
    background-color: transparent !important;
    outline: none !important;
}

hr,
footer,
.footer,
.api-docs,
.built-with,
.settings {
    display: none !important;
}

.header {
    display: flex;
    justify-content: center !important;
    align-items: center;
    background: #FFFFFF !important;
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 24px 28px;
    margin: 0 0 24px 0;
    box-shadow: 0 4px 14px rgba(108, 78, 234, 0.045);
}

.logo-wrap {
    display: flex;
    align-items: center;
    gap: 14px;
}


.logo-image {
    width: 58px !important;
    height: 58px !important;
    border-radius: 16px !important;
    object-fit: cover !important;
    border: 1px solid var(--border-soft) !important;
    box-shadow: 0 4px 12px rgba(108, 78, 234, 0.08) !important;
}

.hero-logo {
    width: 360px !important;
    max-width: 85% !important;
    height: auto !important;
    border-radius: 28px !important;
    margin: 14px auto 22px auto !important;
    display: block !important;
    box-shadow: 0 8px 24px rgba(108, 78, 234, 0.08) !important;
}

.logo-icon {
    width: 42px;
    height: 42px;
    border-radius: 14px;
    background: linear-gradient(135deg, var(--primary), var(--primary-2)) !important;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #FFFFFF !important;
    font-size: 23px;
    font-weight: 900;
}

.logo-title {
    font-size: 25px !important;
    font-weight: 850;
    color: var(--primary) !important;
    line-height: 1.15 !important;
}

.sub-title {
    margin-top: 4px;
    font-size: 13px !important;
    color: var(--muted) !important;
}

.nav {
    display: none !important;
}

.page-card,
.side-card,
.form-panel {
    background: #FFFFFF !important;
    border: 1px solid var(--border) !important;
    border-radius: 24px !important;
    box-shadow: 0 5px 16px rgba(108, 78, 234, 0.05) !important;
    overflow: visible !important;
}

.page-card {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
}

.side-card {
    padding: 36px 28px 28px 28px;
    min-height: 540px;
}

.form-panel {
    padding: 36px 30px 30px 30px !important;
}

.side-card,
.side-card * {
    overflow: visible !important;
}

.side-title {
    font-size: 25px !important;
    font-weight: 850;
    line-height: 1.35 !important;
    margin: 0 0 14px 0 !important;
    padding-top: 2px !important;
}

.side-desc {
    font-size: 14px !important;
    color: var(--muted) !important;
    line-height: 1.65 !important;
}
`
.main-card {
    max-width: 900px !important;
    width: 100% !important;
    margin: 0 auto;
    text-align: center !important;
}

.hero-title {
    font-size: 31px !important;
    font-weight: 900;
    color: var(--primary) !important;
    line-height: 1.25 !important;
    margin-bottom: 8px;
}

.hero-sub {
    font-size: 16px !important;
    font-weight: 850;
    margin-bottom: 26px;
}

.hero-icon {
    font-size: 82px;
    margin: 8px 0 8px 0 !important;
}

.info-list,
.input-guide,
.source-box {
    background: var(--sub-card) !important;
    border: 1px solid var(--border-soft) !important;
    border-radius: 18px !important;
}

.info-list {
    width: 95% !important;
    max-width: 980px !important;
    padding: 32px 40px !important;
    margin-top: 30px !important;
    margin-bottom: 80px !important;
}

.input-guide {
    margin-top: 28px;
    padding: 22px;
}

.source-box {
    padding: 18px 20px;
    margin-top: 16px;
}

.info-row {
    display: flex;
    align-items: flex-start;
    gap: 14px;
    margin: 16px 0;

    font-size: 24px !important;
    line-height: 1.8 !important;
    font-weight: 600 !important;
}

.info-row span:not(.icon) {
    font-size: 24px !important;
}

.info-row .icon {
    color: var(--success) !important;
    font-weight: 900;
    min-width: 32px;

    font-size: 22px !important;
}

/* 직접 작성한 카테고리 라벨 */
.form-label {
    display: inline-block !important;
    width: fit-content !important;
    background: var(--label-bg) !important;
    color: var(--label-text) !important;
    padding: 8px 14px !important;
    margin: 0 0 10px 0 !important;
    border-radius: 8px !important;
    font-size: 15px !important;
    font-weight: 900 !important;
    line-height: 1.4 !important;
}

/* Gradio 기본 label 숨김/초기화 */
.form-panel label,
.form-panel legend,
.form-panel .label-wrap {
    background: transparent !important;
    color: var(--text) !important;
    padding: 0 !important;
    margin: 0 !important;
    border: none !important;
}

/* 입력 컴포넌트 간격 */
.form-item {
    margin-bottom: 18px !important;
}

.form-item .block,
.form-item .form,
.form-item .wrap,
.form-item .input-container {
    background: #FFFFFF !important;
    overflow: visible !important;
}

input,
textarea,
select {
    background: #FFFFFF !important;
    color: var(--text) !important;
    border: 1.5px solid #DCD3F6 !important;
    border-radius: 12px !important;
    box-shadow: none !important;
    font-size: 14px !important;
}

input::placeholder,
textarea::placeholder {
    color: #888888 !important;
}

input:focus,
textarea:focus,
select:focus {
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 3px rgba(108, 78, 234, 0.12) !important;
}

/* CheckboxGroup */
.form-panel fieldset {
    background: #FFFFFF !important;
    color: var(--text) !important;
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
    padding: 0 !important;
    margin: 0 !important;
    overflow: visible !important;
    display: block !important;
}

.form-panel fieldset > div {
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 10px !important;
    margin-top: 0 !important;
    padding-left: 0 !important;
    overflow: visible !important;
}

.form-panel fieldset label {
    display: inline-flex !important;
    align-items: center !important;
    min-height: 42px !important;
    padding: 8px 14px !important;

    background: transparent !important;
    border: none !important;
    box-shadow: none !important;

    font-size: 15px !important;
    font-weight: 700 !important;
}

.form-panel fieldset label span {
    background: transparent !important;
    color: var(--text) !important;
    padding: 0 !important;
    margin: 0 !important;
    border-radius: 0 !important;
    font-size: 13px !important;
    font-weight: 700 !important;
    line-height: 1.4 !important;
    white-space: nowrap !important;
}

input[type="checkbox"] {
    appearance: none !important;
    -webkit-appearance: none !important;
    width: 17px !important;
    height: 17px !important;
    min-width: 17px !important;
    min-height: 17px !important;
    border: 1.8px solid #BDB7DB !important;
    border-radius: 5px !important;
    background: #FFFFFF !important;
    display: inline-grid !important;
    place-content: center !important;
    margin: 0 8px 0 0 !important;
    padding: 0 !important;
    vertical-align: middle !important;
    box-sizing: border-box !important;
}

input[type="checkbox"]::before {
    content: "✓";
    font-size: 13px;
    font-weight: 900;
    line-height: 1;
    color: #FFFFFF !important;
    transform: scale(0);
}

input[type="checkbox"]:checked {
    background: var(--primary) !important;
    border-color: var(--primary) !important;
}

input[type="checkbox"]:checked::before {
    transform: scale(1);
}

.form-panel fieldset label:has(input[type="checkbox"]:checked) {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    font-weight: 800 !important;
}

.clean-row {
    border-top: none !important;
    box-shadow: none !important;
}

.clean-row > .button-row,
.clean-row > .button-row * {
    border-top: none !important;
    box-shadow: none !important;
}

.result-card {
    position: relative;
    display: flex;
    gap: 16px;
    align-items: center;
    background: #FFFFFF !important;
    border: 1px solid var(--border) !important;
    border-radius: 16px !important;
    padding: 18px 20px;
    margin-bottom: 14px;
    box-shadow: 0 4px 14px rgba(108, 78, 234, 0.05) !important;
}

.result-icon {
    width: 42px;
    height: 42px;
    min-width: 42px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #FFFFFF !important;
    font-size: 20px;
    font-weight: 900;
}

.icon-green { background: var(--success) !important; }
.icon-blue { background: var(--info) !important; }
.icon-orange { background: var(--warning) !important; }

.result-body h3 {
    font-size: 17px !important;
    font-weight: 850;
    margin: 0 0 5px 0;
}

.result-body p,
.result-body li {
    font-size: 13px !important;
    line-height: 1.55 !important;
    margin: 3px 0;
}

.rank {
    position: absolute;
    top: 18px;
    right: 18px;
    padding: 5px 11px;
    border-radius: 9px;
    font-size: 12px !important;
    font-weight: 800;
}

.rank1 {
    background: #E7F8E8 !important;
    color: #2F8F3A !important;
}

.rank2 {
    background: #EAF3FF !important;
    color: #2674C8 !important;
}

.rank3 {
    background: #FFF1DF !important;
    color: #E27913 !important;
}

.green-box {
    background: #F3FFF5 !important;
    border: 1px solid #BDE5C5 !important;
    border-radius: 16px;
    padding: 18px 20px;
    margin-top: 16px;
}

.red-box {
    background: #FFF4F4 !important;
    border: 1px solid #FFC5C5 !important;
    border-radius: 16px;
    padding: 18px 20px;
    margin-top: 16px;
}

.section-title {
    font-size: 18px !important;
    font-weight: 850;
    margin-bottom: 10px;
}

button {
    border-radius: 14px !important;
    box-shadow: none !important;
    font-size: 14px !important;
}

.primary-btn button,
.primary-btn {
    background: linear-gradient(90deg, var(--primary), var(--primary-2)) !important;
    color: #FFFFFF !important;
    border: none !important;
    height: 50px !important;
    font-weight: 850 !important;
}

.primary-btn button *,
.primary-btn * {
    color: #FFFFFF !important;
}

.secondary-btn button,
.secondary-btn {
    background: #FFFFFF !important;
    color: var(--text) !important;
    border: 1px solid #DED7EA !important;
    height: 48px !important;
    font-weight: 750 !important;
}

.footer-custom {
    margin-top: 26px;
    background: #FFFFFF !important;
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 14px;
    text-align: center;
    font-size: 12px !important;
    color: var(--muted) !important;
    box-shadow: 0 4px 14px rgba(108, 78, 234, 0.04);
}

.progress-text,
.generating {
    display: none !important;
}


.result-wide-page,
.evidence-wide-page {
    width: 100% !important;
    max-width: 1040px !important;
    margin: 0 auto !important;
    background: #FFFFFF !important;
    border: 1px solid var(--border) !important;
    border-radius: 24px !important;
    padding: 30px !important;
    box-sizing: border-box !important;
    box-shadow: 0 5px 16px rgba(108, 78, 234, 0.05) !important;
}

.result-wide-page *,
.evidence-wide-page * {
    color: var(--text) !important;
}

.result-wide-page .muted-text,
.evidence-wide-page .muted-text {
    color: #555555 !important;
    font-weight: 700 !important;
}

.result-wide-page .sub-label,
.evidence-wide-page .sub-label {
    color: #666666 !important;
    font-weight: 850 !important;
    margin: 8px 0 4px 0 !important;
}

.result-wide-page ul,
.evidence-wide-page ul {
    padding-left: 20px !important;
}

.result-wide-page li,
.evidence-wide-page li {
    color: #1F1F1F !important;
}

.result-wide-page .result-card,
.evidence-wide-page .result-card {
    width: 100% !important;
    box-sizing: border-box !important;
}

.evidence-wide-page .result-body,
.result-wide-page .result-body {
    padding-right: 88px !important;
}


.loading-page-card {
    width: 100% !important;
    max-width: 1280px !important;
    min-height: 560px !important;
    margin: 0 auto !important;
    background: #FFFFFF !important;
    border: 1px solid var(--border) !important;
    border-radius: 24px !important;
    padding: 30px !important;
    box-sizing: border-box !important;
    box-shadow: 0 5px 16px rgba(108, 78, 234, 0.05) !important;

    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
    align-items: center !important;
    text-align: center !important;
}

.loading-spinner {
    width: 68px !important;
    height: 68px !important;
    border: 7px solid #E5DAFF !important;
    border-top: 7px solid var(--primary) !important;
    border-radius: 50% !important;
    animation: loadingSpin 1s linear infinite !important;
    margin-bottom: 24px !important;
}

@keyframes loadingSpin {
    from {
        transform: rotate(0deg);
    }
    to {
        transform: rotate(360deg);
    }
}

.loading-title {
    font-size: 24px !important;
    font-weight: 900 !important;
    color: var(--primary) !important;
    margin-bottom: 10px !important;
}

.loading-desc {
    font-size: 15px !important;
    color: var(--muted) !important;
    line-height: 1.7 !important;
    margin-bottom: 22px !important;
}

.loading-step-box {
    width: 100% !important;
    max-width: 520px !important;
    background: var(--sub-card) !important;
    border: 1px solid var(--border-soft) !important;
    border-radius: 18px !important;
    padding: 18px 22px !important;
    text-align: left !important;
}

.loading-step {
    display: flex !important;
    align-items: center !important;
    gap: 10px !important;
    font-size: 14px !important;
    line-height: 1.7 !important;
    color: var(--text) !important;
}

.loading-step span:first-child {
    color: var(--primary) !important;
    font-weight: 900 !important;
}

@media (max-width: 768px) {
    .gradio-container {
        padding: 14px !important;
    }

    .header {
        padding: 20px;
    }

    .logo-title {
        font-size: 21px !important;
    }

    .page-card,
    .side-card,
    .form-panel {
        padding: 22px;
        min-height: auto;
    }

    .hero-title {
        font-size: 42px !important;
    }
}
"""

LAST_RESULT = {}


def show_input():
    return (
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=False),
    )


def show_start():
    return (
        gr.update(visible=True),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=False),
    )


def show_result_page():
    return (
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(visible=False),
    )


def show_evidence():
    return (
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=True),
    )


def show_loading():
    return (
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(value=None, visible=False),
    )


def build_result_html(result):
    stage = result["stage"]
    recommendations = result["recommendations"]
    caution_evidences = result.get("cautions", [])
    llm_cautions = result.get("llm_cautions", [])
    user_input = result["input"]
    llm_summary = result.get("llm_summary", "")

    icon_classes = ["icon-green", "icon-blue", "icon-orange"]
    icons = ["🌿", "💧", "🟠"]
    rank_classes = ["rank1", "rank2", "rank3"]

    cards = ""

    for idx, rec in enumerate(recommendations, start=1):
        trigger = ", ".join(rec.get("triggers", []))
        status = rec.get("filter_status", "추천가능")
        products = rec.get("supplements", []) or []

        if products:
            product_items = "".join([
                f"<li>{p.get('product_name', '')} / {p.get('manufacturer', '')} / {p.get('registration_date', '')}</li>"
                for p in products
            ])
            product_html = f"<p class='muted-text'><b>영양제 후보</b></p><ul>{product_items}</ul>"
        else:
            product_html = "<p class='muted-text'>영양제 후보: 현재 CSV에서 매칭된 제품 없음 또는 복용 중 제품과 중복 제거됨</p>"

        cards += f"""
        <div class="result-card">
            <div class="result-icon {icon_classes[idx - 1]}">
                {icons[idx - 1]}
            </div>

            <div class="result-body">
                <h3>{rec.get("nutrient")}</h3>
                <p class="muted-text">관련 입력: {trigger}</p>
                <p class="muted-text">필터링 결과: {status}</p>
                {product_html}
            </div>

            <span class="rank {rank_classes[idx - 1]}">우선순위 {idx}</span>
        </div>
        """

    symptom_text = ", ".join(user_input["symptoms"]) if user_input["symptoms"] else "없음"
    diet_text = ", ".join(user_input["diets"]) if user_input["diets"] else "없음"
    intake_text = user_input["intake_text"] if user_input["intake_text"] else "없음"

    if llm_cautions:
        caution_html = "".join([
            f"<li>{c}</li>"
            for c in llm_cautions
        ])
    else:
        caution_html = """
        <li>권장 섭취량을 초과하지 않도록 주의하세요.</li>
        <li>영양제나 의약품 복용은 전문가와 상담하세요.</li>
        """

    source_set = []

    for rec in recommendations:
        source_set.extend(rec.get("sources", []))

    for caution in caution_evidences:
        if caution.get("source"):
            source_set.append(caution.get("source"))

    source_set = list(dict.fromkeys([x for x in source_set if x]))

    if not source_set:
        source_set = [
            "공공데이터포털(MFDS)_의약품개요정보(e약은요)",
            "공공데이터포털(MFDS)_의약품 제품 허가정보",
            "공공데이터포털(MFDS)_건강기능식품 품목분류정보",
            "국가건강정보포털(질병관리청)_정상임신관리(임신의 진단과 관리)",
            "국가건강정보포털(질병관리청)_식이영양(임산부)"
        ]

    source_html = "".join([f"<li>{src}</li>" for src in source_set])

    if llm_summary:
        summary_text = llm_summary
    else:
        summary_text = (
            "입력하신 증상과 생활습관을 바탕으로 부족할 가능성이 높은 "
            "영양소를 우선순위로 추천했습니다."
        )

    html = f"""
    <div class="result-wide-page">
        <div style="text-align:center; margin-bottom:22px;">
            <div style="
                font-size:21px;
                font-weight:900;
                color:#111 !important;
                margin-bottom:8px;
            ">
                맞춤 영양 추천 결과
            </div>

            <div style="font-size:14px; color:#555 !important;">
                임신 {user_input["week"]}주 · {stage.get("stage_name", "단계 정보 없음")}
            </div>

            <div style="font-size:13px; color:#555 !important; margin-top:8px;">
                <b>증상:</b> {symptom_text} ·
                <b>생활습관:</b> {diet_text} ·
                <b>복용 정보:</b> {intake_text}
            </div>
        </div>

        <div style="
            font-size:15px;
            font-weight:850;
            color:#6C4EEA !important;
            margin-bottom:12px;
        ">
            추천 영양 성분 TOP 3
        </div>

        {cards}

        <div class="green-box">
            <div class="section-title">추천 이유</div>
            <p>{summary_text}</p>
        </div>

        <div class="red-box">
            <div class="section-title">주의사항</div>
            <ul>{caution_html}</ul>
        </div>

        <div class="source-box">
            <div class="section-title">참고 자료</div>
            <ul>{source_html}</ul>
        </div>
    </div>
    """

    return html

def build_evidence_html(result):
    recommendations = result["recommendations"]
    cautions = result.get("cautions", [])
    user_input = result["input"]

    rec_html = ""

    icon_classes = ["icon-green", "icon-blue", "icon-orange"]
    rank_classes = ["rank1", "rank2", "rank3"]

    for idx, rec in enumerate(recommendations, start=1):
        reasons = "".join([
            f"<li>{reason}</li>"
            for reason in rec.get("reasons", [])
        ])

        sources = "".join([
            f"<li>{source}</li>"
            for source in rec.get("sources", [])
        ])

        rec_html += f"""
        <div class="result-card">
            <div class="result-icon {icon_classes[idx - 1]}">{idx}</div>

            <div class="result-body">
                <h3>{rec.get("nutrient")}</h3>

                <p class="sub-label">추천 근거</p>
                <ul>{reasons}</ul>

                <p class="sub-label">출처</p>
                <ul>{sources}</ul>

                <p class="sub-label">영양제 후보</p>
                <ul>{''.join([f"<li>{p.get('product_name', '')} / {p.get('manufacturer', '')} / {p.get('registration_date', '')}</li>" for p in rec.get('supplements', [])]) or '<li>매칭된 제품 없음</li>'}</ul>
            </div>

            <span class="rank {rank_classes[idx - 1]}">근거</span>
        </div>
        """

    if cautions:
        caution_html = "".join([
            f"<li>{c.get('evidence') or c.get('warning', '')}</li>"
            for c in cautions
        ])
    else:
        caution_html = "<li>DB에서 조회된 추가 주의사항은 없습니다.</li>"

    supplements_text = ", ".join(user_input.get("supplements", [])) or "없음"
    medicines_text = ", ".join(user_input.get("medicines", [])) or "없음"
    caution_items_text = ", ".join(user_input.get("caution_items", [])) or "없음"

    parsed_html = f"""
    <ul>
        <li><b>LLM 분석 supplements:</b> <span>{supplements_text}</span></li>
        <li><b>LLM 분석 medicines:</b> <span>{medicines_text}</span></li>
        <li><b>LLM 분석 caution_items:</b> <span>{caution_items_text}</span></li>
    </ul>
    """

    html = f"""
    <div class="evidence-wide-page">
        <div style="margin-bottom:22px;">
            <div style="
                font-size:21px;
                font-weight:900;
                color:#111 !important;
                margin-bottom:8px;
            ">
                추천 근거 및 출처
            </div>

            <p class="muted-text">추천된 영양 성분별 DB 조회 근거입니다.</p>
        </div>

        {rec_html}

        <div class="green-box">
            <div class="section-title">복용 정보 LLM 분석 결과</div>
            {parsed_html}
        </div>

        <div class="red-box">
            <div class="section-title">주의사항 근거</div>
            <ul>{caution_html}</ul>
        </div>
    </div>
    """

    return html

def recommend_from_engine(
    week,
    symptoms,
    diets,
    intake_text
):
    global LAST_RESULT

    if week is None:
        raise gr.Error("임신 주차를 입력하세요.")

    result = run_recommendation(
        week=int(week),
        symptoms=symptoms or [],
        diets=diets or [],
        intake_text=intake_text or "",
        use_llm_intake=True,
        use_llm_summary=True,
        use_llm_caution=True
    )

    LAST_RESULT = result

    result_html = build_result_html(result)
    evidence_html = build_evidence_html(result)

    return (
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=True),
        result_html,
        evidence_html
    )


def save_pdf(progress=gr.Progress()):
    global LAST_RESULT

    if not LAST_RESULT:
        raise gr.Error("먼저 추천 결과를 생성하세요.")

    progress(0.3, desc="PDF 저장을 준비하고 있습니다.")
    pdf_path = export_recommendation_pdf(LAST_RESULT)
    progress(1.0, desc="PDF 저장이 완료되었습니다.")

    return gr.update(value=pdf_path, visible=True)

def build_app():
    theme = gr.themes.Soft(
        primary_hue="violet",
        neutral_hue="gray"
    )

    with gr.Blocks(
        css=CSS,
        title="Mom's Nutrition Guide",
        theme=theme
    ) as demo:

        gr.HTML(f"""
        <div class="header">
            <div class="logo-wrap">
                <img class="logo-image" src="{LOGO_DATA_URI}" alt="Mom's Nutrition Guide logo">
                <div>
                    <div class="logo-title">Mom's Nutrition Guide</div>
                    <div class="sub-title">임산부 맞춤 영양 추천 서비스</div>
                </div>
            </div>
        </div>
        """)

        with gr.Group(visible=True, elem_classes=["clean-page"]) as start_page:
            gr.HTML(f"""
            <div class="page-card main-card">
                <div class="hero-title"><br>Mom's Nutrition Guide<br></div>
                <div class="hero-sub">임산부 맞춤 영양 추천 서비스</div>

                <img class="hero-logo" src="{LOGO_DATA_URI}" alt="임산부 맞춤 영양 추천 서비스 로고">

                <div class="info-list">
                    <div class="info-row">
                        <span class="icon">✓</span>
                        <span>임신 주차, 증상, 건강상태를 입력하면 필요한 영양소를 추천합니다.</span>
                    </div>
                    <div class="info-row">
                        <span class="icon">✓</span>
                        <span>공공기관 데이터를 기반으로 근거 있는 정보를 제공합니다.</span>
                    </div>
                    <div class="info-row">
                        <span class="icon">✓</span>
                        <span>주의사항과 근거 출처까지 함께 확인할 수 있습니다.</span>
                    </div>
                </div>
            </div>
            """)

            start_btn = gr.Button("시작하기  →", elem_classes=["primary-btn"])

        with gr.Group(visible=False, elem_classes=["clean-page"]) as input_page:
            with gr.Row(elem_classes=["clean-row"]):
                with gr.Column(scale=4, elem_classes=["clean-column"]):
                    gr.HTML("""
                    <div class="side-card">
                        <div class="side-title">입력 폼 화면</div>
                        <div class="side-desc">
                            임신 주차, 현재 증상, 건강상태, 복용 정보를 입력하세요.
                        </div>

                        <div class="input-guide">
                            <h3>입력 항목</h3>
                            <ul>
                                <li>임신 주차</li>
                                <li>현재 증상</li>
                                <li>생활습관 체크</li>
                                <li>복용 중 영양제/의약품</li>
                            </ul>
                        </div>

                        <div class="info-list">
                            <div class="info-row">
                                <span class="icon">📝</span>
                                <span>체크박스를 선택하면 추천 결과에 바로 반영됩니다.</span>
                            </div>
                            <div class="info-row">
                                <span class="icon">🔎</span>
                                <span>복용 정보는 AI가 영양제/의약품명으로 정리합니다.</span>
                            </div>
                        </div>
                    </div>
                    """)

                with gr.Column(scale=6, elem_classes=["form-panel"]):

                    with gr.Group(elem_classes=["form-item"]):
                        gr.HTML('<div class="form-label">임신 주차</div>')
                        week = gr.Number(
                            label=None,
                            show_label=False,
                            value=None,
                            minimum=1,
                            maximum=42
                        )

                    with gr.Group(elem_classes=["form-item"]):
                        gr.HTML('<div class="form-label">주요 증상</div>')
                        symptoms = gr.CheckboxGroup(
                            choices=["입덧", "변비", "빈혈"],
                            label=None,
                            show_label=False,
                            value=None
                        )

                    with gr.Group(elem_classes=["form-item"]):
                        gr.HTML('<div class="form-label">생활습관 체크</div>')
                        diets = gr.CheckboxGroup(
                            choices=[
                                "채소·과일 섭취가 부족함",
                                "신체활동이 부족함",
                                "한 번에 많은 양을 섭취함",
                                "철분 섭취가 부족함",
                                "식이섬유 섭취가 부족함",
                                "규칙적인 식사를 하지 않음"
                            ],
                            label=None,
                            show_label=False,
                            value=None
                        )

                    with gr.Group(elem_classes=["form-item"]):
                        gr.HTML('<div class="form-label">현재 복용 중인 영양제/의약품</div>')
                        intake_text = gr.Textbox(
                            label=None,
                            show_label=False,
                            placeholder="예: 철분제, 유산균, 비타민D",
                            lines=2
                        )

                    with gr.Row(elem_classes=["clean-row"]):
                        back_btn = gr.Button("처음으로", elem_classes=["secondary-btn"])
                        recommend_btn = gr.Button("다음  →", elem_classes=["primary-btn"])

        with gr.Group(visible=False, elem_classes=["clean-page"]) as loading_page:
            gr.HTML("""
            <div class="loading-page-card">
                <div class="loading-spinner"></div>

                <div class="loading-title">
                    맞춤 영양 추천 생성 중
                </div>

                <div class="loading-desc">
                    입력하신 임신 주차, 증상, 건강상태, 복용 정보를 분석하고 있습니다.<br>
                    LLM 기반 복용 정보 분석과 추천 이유 생성을 진행 중입니다.
                </div>

                <div class="loading-step-box">
                    <div class="loading-step">
                        <span>1</span>
                        <span>입력 정보 확인</span>
                    </div>
                    <div class="loading-step">
                        <span>2</span>
                        <span>복용 정보 LLM 분석</span>
                    </div>
                    <div class="loading-step">
                        <span>3</span>
                        <span>CSV 기반 영양 성분 추천</span>
                    </div>
                    <div class="loading-step">
                        <span>4</span>
                        <span>추천 이유 및 주의사항 정리</span>
                    </div>
                </div>
            </div>
            """)

        with gr.Group(visible=False, elem_classes=["clean-page"]) as result_page:
            result_html = gr.HTML()

            with gr.Row(elem_classes=["clean-row"]):
                evidence_btn = gr.Button("근거 보기", elem_classes=["secondary-btn"])
                retry_btn = gr.Button("다시 입력하기", elem_classes=["secondary-btn"])
                pdf_btn = gr.Button("PDF로 저장", elem_classes=["primary-btn"])

            pdf_file = gr.File(
                label="PDF 다운로드",
                visible=False
            )

        with gr.Group(visible=False, elem_classes=["clean-page"]) as evidence_page:
            evidence_html = gr.HTML()
            evidence_back_btn = gr.Button("결과로 돌아가기", elem_classes=["primary-btn"])

        gr.HTML("""
        <div class="footer-custom">
            API를 통해 사용 🚀 · Gradio로 제작됨 📦 · 설정 ⚙️
        </div>
        """)

        start_btn.click(
            fn=show_input,
            outputs=[start_page, input_page, loading_page, result_page, evidence_page],
            show_progress="hidden"
        )

        back_btn.click(
            fn=show_start,
            outputs=[start_page, input_page, loading_page, result_page, evidence_page],
            show_progress="hidden"
        )

        recommend_btn.click(
            fn=show_loading,
            inputs=[],
            outputs=[
                start_page,
                input_page,
                loading_page,
                result_page,
                evidence_page,
                pdf_file
            ],
            show_progress="hidden"
        ).then(
            fn=recommend_from_engine,
            inputs=[week, symptoms, diets, intake_text],
            outputs=[
                input_page,
                evidence_page,
                loading_page,
                result_page,
                result_html,
                evidence_html
            ],
            show_progress="hidden"
        )

        retry_btn.click(
            fn=show_input,
            outputs=[start_page, input_page, loading_page, result_page, evidence_page],
            show_progress="hidden"
        )

        evidence_btn.click(
            fn=show_evidence,
            outputs=[start_page, input_page, loading_page, result_page, evidence_page],
            show_progress="hidden"
        )

        evidence_back_btn.click(
            fn=show_result_page,
            outputs=[start_page, input_page, loading_page, result_page, evidence_page],
            show_progress="hidden"
        )

        pdf_btn.click(
            fn=save_pdf,
            inputs=[],
            outputs=[pdf_file],
            show_progress="full"
        )

    return demo