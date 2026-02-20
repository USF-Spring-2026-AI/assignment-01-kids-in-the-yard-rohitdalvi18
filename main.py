from person_factory import PersonFactory
from family_tree import FamilyTree


def main():
    pf = PersonFactory(data_dir=".")
    pf.read_files()

    tree = FamilyTree(pf)
    tree.generate_tree()
    tree.run_menu()


if __name__ == "__main__":
    main()
