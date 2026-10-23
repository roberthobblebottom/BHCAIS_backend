from fastapi import HTTPException
from pytest import raises

from src.Models import password_validation


def test_password_validation():
    print("testing password validation")

    other_passwords = ["878", "hase", "123456789", "abcdefghijkl", "password"]
    for p in other_passwords:
        with raises(HTTPException) as e_info:
            password_validation(p)
        error = str(e_info.value)
        print("EXPECTED ERROR:", error)
        assert "442: " in error
