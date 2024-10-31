import asyncio
from enum import Enum
from pathlib import Path
import sys
from typing import Final


class TermColor(Enum):
    RED = "\033[91m"
    GREEN = "\033[92m"
    RESET = "\033[0m"


class TestsDir(Enum):
    OK = "ok"
    NOT_OK = "not_ok"
    TWICE = "twice"


def add_color(message: str, color: TermColor) -> str:
    return f"{color.value}{message}{TermColor.RESET.value}"


MSG_OK: Final[str] = add_color("OK", TermColor.GREEN)
MSG_FAILED: Final[str] = add_color("FAILED", TermColor.RED)
MSG_PASSED: Final[str] = add_color("PASSED", TermColor.GREEN)

INPUT_IMAGE: Final[str] = "image.bmp"
OUTPUT_IMAGE: Final[str] = "image_neg.bmp"
REFERENCE_IMAGE: Final[str] = "image_neg_reference.bmp"
OUTPUT_TWICE_IMAGE: Final[str] = "image_neg_twice.bmp"

IMAGES_SAME_MESSAGE: Final[str] = "Images are same"


async def run_all_tests(test_data_dir: Path, converter: Path, comparer: Path) -> int:
    ok_tests_dir = Path.joinpath(test_data_dir, TestsDir.OK.value)
    not_ok_tests_dir = Path.joinpath(test_data_dir, TestsDir.NOT_OK.value)
    twice_tests_dir = Path.joinpath(test_data_dir, TestsDir.TWICE.value)
    failed_tests = await asyncio.gather(
        run_ok_tests(ok_tests_dir, converter, comparer),
        run_not_ok_tests(not_ok_tests_dir, converter),
        run_twice_tests(twice_tests_dir, converter, comparer),
    )
    return sum(failed_tests)


async def run_ok_tests(tests_dir: Path, converter: Path, comparer: Path) -> int:
    failed_tests = 0
    for test in sorted(map(lambda p: p.stem, tests_dir.iterdir())):
        image_in = Path.joinpath(tests_dir, test, INPUT_IMAGE)
        image_out = Path.joinpath(tests_dir, test, OUTPUT_IMAGE)
        image_out_ref = Path.joinpath(tests_dir, test, REFERENCE_IMAGE)
        rc_actual, out_actual, err_actual = await run_test(
            converter,
            (image_in, image_out)
        )
        if not await validate_ok_test(
            test,
            comparer,
            (image_out, image_out_ref),
            (0, rc_actual),
            ("", out_actual),
            ("", err_actual),
        ):
            failed_tests += 1
        if image_out.exists():
            image_out.unlink()
    return failed_tests


async def run_not_ok_tests(tests_dir: Path, converter: Path) -> int:
    failed_tests = 0
    for test in sorted(map(lambda p: p.stem, tests_dir.iterdir())):
        image_in = Path.joinpath(tests_dir, test, INPUT_IMAGE)
        image_out = Path.joinpath(tests_dir, test, OUTPUT_IMAGE)
        rc_actual, out_actual, err_actual = await run_test(
            converter,
            (image_in, image_out)
        )
        if not validate_not_ok_test(
            test,
            image_out,
            (1, rc_actual),
            ("", out_actual),
            ("", err_actual),
        ):
            failed_tests += 1
        if image_out.exists():
            image_out.unlink()
    return failed_tests


async def run_twice_tests(tests_dir: Path, converter: Path, comparer: Path) -> int:
    failed_tests = 0
    for test in sorted(map(lambda p: p.stem, tests_dir.iterdir())):
        image_in = Path.joinpath(tests_dir, test, INPUT_IMAGE)
        image_out = Path.joinpath(tests_dir, test, OUTPUT_IMAGE)
        image_out_twice = Path.joinpath(tests_dir, test, OUTPUT_TWICE_IMAGE)
        rc_actual, out_actual, err_actual = await run_test(
            converter,
            (image_in, image_out)
        )
        await run_test(
            converter,
            (image_out, image_out_twice)
        )

        if not await validate_ok_test(
            test,
            comparer,
            (image_in, image_out_twice),
            (0, rc_actual),
            ("", out_actual),
            ("", err_actual),
        ):
            failed_tests += 1
        if image_out.exists():
            image_out.unlink()
        if image_out_twice.exists():
            image_out_twice.unlink()
    return failed_tests


async def run_test(
    converter: Path,
    images: tuple[Path, Path],
) -> tuple[int, str, str]:
    image_in, image_out = images
    if image_out.exists():
        image_out.unlink()
    proc = await asyncio.create_subprocess_exec(
        converter, image_in, image_out,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await proc.communicate()
    rc = await proc.wait()
    out_text = stdout.decode("ascii", "replace").strip()
    err_text = stderr.decode("ascii", "replace").strip()
    return rc, out_text, err_text


async def validate_ok_test(
    test_name: str,
    comparer: Path,
    imgs: tuple[Path, Path],
    rcs: tuple[int, int],
    outs: tuple[str, str],
    errs: tuple[str, str],
) -> bool:
    rc_expected, rc_actual = rcs
    if rc_expected != rc_actual:
        print(f"{MSG_FAILED} {test_name}: Return code {rc_expected} != {rc_actual}")
        return False
    out_expected, out_actual = outs
    if out_expected != out_actual:
        print(f"{MSG_FAILED} {test_name}: incorrect stdout")
        return False
    err_expected, err_actual = errs
    if err_expected != err_actual:
        print(f"{MSG_FAILED} {test_name}: incorrect stderr")
        return False

    proc = await asyncio.create_subprocess_exec(
        comparer, imgs[0], imgs[1],
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await proc.communicate()
    rc = await proc.wait()
    out_text = stdout.decode("ascii", "replace").strip()
    err_text = stderr.decode("ascii", "replace").strip()
    if rc != 0 or out_text != IMAGES_SAME_MESSAGE or err_text != "":
        print(f"{MSG_FAILED} {test_name}: result image is incorrect")
        return False
    print(f"{MSG_OK} {test_name}")
    return True


def validate_not_ok_test(
    test_name: str,
    image_out: Path,
    rcs: tuple[int, int],
    outs: tuple[str | None, str],
    errs: tuple[str, str],
) -> bool:
    rc_expected, rc_actual = rcs
    if rc_expected != rc_actual:
        print(f"{MSG_FAILED} {test_name}: return code {rc_expected} != {rc_actual}")
        return False
    out_expected, out_actual = outs
    if out_expected != out_actual:
        print(f"{MSG_FAILED} {test_name}: incorrect stdout")
        return False
    _, err_actual = errs
    if not err_actual:
        print(f"{MSG_FAILED} {test_name}: incorrect stderr")
        return False
    if image_out.exists():
        print(f"{MSG_FAILED} {test_name}: output file created in incorect scenario")
        return False
    print(f"{MSG_OK} {test_name}")
    return True


def main() -> int:
    converter = Path(sys.argv[1]).absolute()
    tests_dir = Path(sys.argv[2]).absolute()
    comparer = Path(sys.argv[3]).absolute()
    failed_tests: int = asyncio.run(run_all_tests(tests_dir, converter, comparer))
    if failed_tests > 0:
        print(f"{failed_tests} tests {MSG_FAILED}\n")
        return 1
    print(f"All tests {MSG_PASSED}\n")
    return 0


if __name__ == "__main__":
    rc = main()
    sys.exit(rc)
