from codepick_l3.briefs import generate_public_brief
from codepick_l3.provider import get_content_provider


def main() -> None:
    brief = generate_public_brief(get_content_provider())
    assert brief.items, "brief must contain items"
    print(f"Generated brief {brief.id} with {len(brief.items)} items")


if __name__ == "__main__":
    main()

