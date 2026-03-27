#!/usr/bin/env python3
"""
Quick HTTP verification of ACDelco and Moog part numbers
"""

import requests
import time

def test_acdelco_parts():
    """Test common ACDelco part numbers via HTTP"""
    print("ACDELCO/GMPARTS QUICK VERIFICATION")
    print("=" * 40)

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })

    # Common ACDelco part patterns to test
    test_parts = [
        # Oil filters
        "PF454", "PF46", "PF1218", "PF2232",
        # Air filters
        "A1195C", "A3097C", "A3144C",
        # Spark plugs
        "41-103", "41-101", "41-993",
        # Brake parts
        "18A1324A", "18A1556A", "18A1557A",
        # AC parts with numbers
        "AC45", "AC46", "AC47", "AC48"
    ]

    verified = []

    for part in test_parts:
        # Try GMParts URL format
        test_urls = [
            f"https://www.gmparts.com/p-{part}.aspx",
            f"https://www.gmparts.com/parts/{part}",
            f"https://www.acdelco.com/parts/{part}"
        ]

        for url in test_urls:
            try:
                response = session.get(url, timeout=10)
                if response.status_code == 200:
                    content = response.text.lower()
                    # Check if it contains the part number and product keywords
                    if (part.lower() in content and
                        any(keyword in content for keyword in ['product', 'specification', 'description', 'part', 'vehicle', 'acdelco', 'genuine'])):

                        verified.append({
                            'part_number': part,
                            'url': url,
                            'status': 'VERIFIED'
                        })
                        print(f"[VERIFIED] {part} -> {url}")
                        break
                elif response.status_code == 404:
                    continue
                else:
                    print(f"[HTTP {response.status_code}] {part} at {url}")
            except:
                continue

        if len(verified) >= 3:
            break

        time.sleep(0.5)  # Rate limiting

    return verified

def test_moog_parts():
    """Test common Moog part numbers via HTTP"""
    print("\nMOOG QUICK VERIFICATION")
    print("=" * 40)

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })

    # Common Moog part patterns to test
    test_parts = [
        # Chassis parts
        "K80145", "K80146", "K80147", "K80148",
        # End links
        "K90449", "K90450", "K90451",
        # Ball joints
        "K500068", "K500069", "K500070",
        # Tie rods
        "ES3470", "ES3471", "ES3472",
        # Control arms
        "RK620124", "RK620125", "RK620126"
    ]

    verified = []

    for part in test_parts:
        # Try Moog URL patterns
        test_urls = [
            f"https://www.moogparts.com/part/{part}",
            f"https://www.moogparts.com/parts/{part}",
            f"https://www.moogparts.com/products/{part}"
        ]

        for url in test_urls:
            try:
                response = session.get(url, timeout=10)
                if response.status_code == 200:
                    content = response.text.lower()
                    # Check if it contains the part number and product keywords
                    if (part.lower() in content and
                        any(keyword in content for keyword in ['product', 'specification', 'description', 'part', 'vehicle', 'moog', 'chassis'])):

                        verified.append({
                            'part_number': part,
                            'url': url,
                            'status': 'VERIFIED'
                        })
                        print(f"[VERIFIED] {part} -> {url}")
                        break
                elif response.status_code == 404:
                    continue
                else:
                    print(f"[HTTP {response.status_code}] {part} at {url}")
            except:
                continue

        if len(verified) >= 3:
            break

        time.sleep(0.5)  # Rate limiting

    return verified

if __name__ == "__main__":
    print("QUICK VERIFICATION OF ACDELCO AND MOOG PARTS")
    print("=" * 50)

    # Test both sites
    acdelco_parts = test_acdelco_parts()
    moog_parts = test_moog_parts()

    # Summary
    print("\n" + "=" * 50)
    print("QUICK VERIFICATION RESULTS")
    print("-" * 25)

    print(f"\nACDELCO/GMPARTS ({len(acdelco_parts)} verified):")
    for part in acdelco_parts:
        print(f"  {part['part_number']}: {part['url']}")

    print(f"\nMOOG ({len(moog_parts)} verified):")
    for part in moog_parts:
        print(f"  {part['part_number']}: {part['url']}")

    total = len(acdelco_parts) + len(moog_parts)
    print(f"\nTOTAL QUICK VERIFIED: {total} parts")

    if total >= 4:
        print("[SUCCESS] Found sufficient parts for initial testing")
    else:
        print(f"[PARTIAL] Need {4 - total} more verified parts")

    # Site assessment
    print(f"\nSITE ASSESSMENT:")
    if acdelco_parts:
        print("  ACDelco/GMParts: READY for scraper development")
    else:
        print("  ACDelco/GMParts: Need alternative part discovery method")

    if moog_parts:
        print("  Moog: READY for scraper development")
    else:
        print("  Moog: Need alternative part discovery method")