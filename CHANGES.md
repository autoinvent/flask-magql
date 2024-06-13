## Version 1.1.0

Unreleased

-   Adjust the default context to support Flask-SQLAlchemy-Lite.
-   Don't register views on each call to `init_app`, which caused issues when
    testing applications that used the app factory pattern.


## Version 1.0.0

Released 2023-07-24

-   Initial release.
