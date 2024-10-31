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
    SAME = "same"
    DIFF = "diff"


def add_color(message: str, color: TermColor) -> str:
    return f"{color.value}{message}{TermColor.RESET.value}"


MSG_OK: Final[str] = add_color("OK", TermColor.GREEN)
MSG_FAILED: Final[str] = add_color("FAILED", TermColor.RED)
MSG_PASSED: Final[str] = add_color("PASSED", TermColor.GREEN)

TEST_IMAGE_1: Final[str] = "image1.bmp"
TEST_IMAGE_2: Final[str] = "image2.bmp"

RC_TOTALLY_DIFFERENT: Final[int] = 1
RC_DIFFERENT: Final[int] = 2
IMAGES_SAME_MESSAGE: Final[str] = "Images are same"


async def run_all_tests(test_data_dir: Path, comparer: Path) -> int:
    same_tests_dir = Path.joinpath(test_data_dir, TestsDir.SAME.value)
    diff_tests_dir = Path.joinpath(test_data_dir, TestsDir.DIFF.value)
    failed_tests = await asyncio.gather(
        run_same_tests(same_tests_dir, comparer),
        run_diff_tests(diff_tests_dir, comparer),
    )
    return sum(failed_tests)


async def run_same_tests(tests_dir: Path, comparer: Path) -> int:
    failed_tests = 0
    for test in sorted(map(lambda p: p.stem, tests_dir.iterdir())):
        image1 = Path.joinpath(tests_dir, test, TEST_IMAGE_1)
        image2 = Path.joinpath(tests_dir, test, TEST_IMAGE_2)
        rc_actual, out_actual, err_actual = await run_test(
            comparer,
            (image1, image2)
        )
        if not validate_test(
            test,
            True,
            (0, rc_actual),
            (IMAGES_SAME_MESSAGE, out_actual),
            ("", err_actual)
        ):
            failed_tests += 1
    return failed_tests


async def run_diff_tests(tests_dir: Path, comparer: Path) -> int:
    failed_tests = 0
    for test in sorted(map(lambda p: p.stem, tests_dir.iterdir())):
        image1 = Path.joinpath(tests_dir, test, TEST_IMAGE_1)
        image2 = Path.joinpath(tests_dir, test, TEST_IMAGE_2)
        stderr_file = Path.joinpath(tests_dir, test, 'output.txt')
        if stderr_file.exists():
            rc_expected, out_expected = RC_DIFFERENT, ""
            with open(stderr_file, "r") as errf:
                err_expected = errf.read().strip()
        else:
            rc_expected, out_expected, err_expected = RC_TOTALLY_DIFFERENT, "", ""
        rc_actual, out_actual, err_actual = await run_test(
            comparer,
            (image1, image2),
        )
        if not validate_test(
            test,
            False,
            (rc_expected, rc_actual),
            (out_expected, out_actual),
            (err_expected, err_actual)
        ):
            failed_tests += 1
    return failed_tests


async def run_test(
    comparer: Path,
    images: tuple[Path, Path],
) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        comparer, images[0], images[1],
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await proc.communicate()
    rc = await proc.wait()
    out_text = stdout.decode("ascii", "replace").strip()
    err_text = stderr.decode("ascii", "replace").strip()
    return rc, out_text, err_text


def validate_test(
    test_name: str,
    are_same: bool,
    rcs: tuple[int, int],
    outs: tuple[str | None, str],
    errs: tuple[str, str],
) -> bool:
    rc_expected, rc_actual = rcs
    if rc_expected != rc_actual:
        print(f"{MSG_FAILED} {test_name}: Return code {rc_expected} != {rc_actual}")
        return False
    if are_same:
        out_expected, out_actual = outs
        if out_expected != out_actual:
            print(f"{MSG_FAILED} {test_name}: incorrect stdout")
            return False
    else:
        err_expected, err_actual = errs
        if (rc_expected == RC_DIFFERENT and err_expected != err_actual) or not err_actual:
            print(f"{MSG_FAILED} {test_name}: incorrect stderr")
            return False
    print(f"{MSG_OK} {test_name}")
    return True


def main() -> int:
    comparer = Path(sys.argv[1]).absolute()
    tests_dir = Path(sys.argv[2]).absolute()
    failed_tests: int = asyncio.run(run_all_tests(tests_dir, comparer))
    if failed_tests > 0:
        print(f"{failed_tests} tests {MSG_FAILED}\n")
        return 1
    print(f"All tests {MSG_PASSED}\n")
    return 0


if __name__ == "__main__":
    rc = main()
    sys.exit(rc)
