from scripts.check_new_handbook import extract_edition_years

def test_handbook_checker_accepts_hyphen_and_en_dash():
    html = "Handbook on Indian Insurance Statistics 2024–25; Insurance Statistics FY 2023-24"
    assert extract_edition_years(html) == ["2023-24", "2024-25"]
