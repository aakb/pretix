from datetime import datetime, timedelta
from decimal import Decimal
from unittest import mock

import pytest
from django_countries.fields import Country
from pytz import UTC

from pretix.base.models import (
    CartPosition, Event, InvoiceAddress, Order, OrderPosition,
)
from pretix.base.models.orders import OrderFee


@pytest.fixture
def variations(item):
    v = list()
    v.append(item.variations.create(value="ChildA1"))
    v.append(item.variations.create(value="ChildA2"))
    return v


@pytest.fixture
def order(event, item, taxrule):
    testtime = datetime(2017, 12, 1, 10, 0, 0, tzinfo=UTC)

    with mock.patch('django.utils.timezone.now') as mock_now:
        mock_now.return_value = testtime
        o = Order.objects.create(
            code='FOO', event=event, email='dummy@dummy.test',
            status=Order.STATUS_PENDING, secret="k24fiuwvu8kxz3y1",
            datetime=datetime(2017, 12, 1, 10, 0, 0, tzinfo=UTC),
            expires=datetime(2017, 12, 10, 10, 0, 0, tzinfo=UTC),
            total=23, payment_provider='banktransfer', locale='en'
        )
        o.fees.create(fee_type=OrderFee.FEE_TYPE_PAYMENT, value=Decimal('0.25'), tax_rate=Decimal('19.00'),
                      tax_value=Decimal('0.05'), tax_rule=taxrule)
        InvoiceAddress.objects.create(order=o, company="Sample company", country=Country('NZ'))
        return o


@pytest.fixture
def order_position(item, order, taxrule, variations):
    op = OrderPosition.objects.create(
        order=order,
        item=item,
        variation=variations[0],
        tax_rule=taxrule,
        tax_rate=taxrule.rate,
        tax_value=Decimal("3"),
        price=Decimal("23"),
        attendee_name="Peter",
        secret="z3fsn8jyufm5kpk768q69gkbyr5f4h6w"
    )
    return op


@pytest.fixture
def cart_position(event, item, variations):
    testtime = datetime(2017, 12, 1, 10, 0, 0, tzinfo=UTC)

    with mock.patch('django.utils.timezone.now') as mock_now:
        mock_now.return_value = testtime
        c = CartPosition.objects.create(
            event=event,
            item=item,
            datetime=datetime.now(),
            expires=datetime.now() + timedelta(days=1),
            variation=variations[0],
            price=Decimal("23"),
            cart_id="z3fsn8jyufm5kpk768q69gkbyr5f4h6w"
        )
        return c


TEST_EVENT_RES = {
    "name": {"en": "Dummy"},
    "live": False,
    "currency": "EUR",
    "date_from": "2017-12-27T10:00:00Z",
    "date_to": None,
    "date_admission": None,
    "is_public": False,
    "presale_start": None,
    "presale_end": None,
    "location": None,
    "slug": "dummy",
    "has_subevents": False,
    "meta_data": {"type": "Conference"},
    'plugins': {
        'pretix.plugins.banktransfer',
        'pretix.plugins.ticketoutputpdf'
    }
}


@pytest.fixture
def item(event):
    return event.items.create(name="Budget Ticket", default_price=23)


@pytest.fixture
def free_item(event):
    return event.items.create(name="Free Ticket", default_price=0)


@pytest.fixture
def free_quota(event, free_item):
    q = event.quotas.create(name="Budget Quota", size=200)
    q.items.add(free_item)
    return q


@pytest.mark.django_db
def test_event_list(token_client, organizer, event):
    resp = token_client.get('/api/v1/organizers/{}/events/'.format(organizer.slug))
    assert resp.status_code == 200
    print(resp.data)
    assert TEST_EVENT_RES == resp.data['results'][0]


@pytest.mark.django_db
def test_event_create(token_client, organizer, event):
    resp = token_client.post(
        '/api/v1/organizers/{}/events/'.format(organizer.slug),
        {
            "name": {
                "de": "Demo Konference 2020 Test",
                "en": "Demo Conference 2020 Test"
            },
            "live": False,
            "currency": "EUR",
            "date_from": "2017-12-27T10:00:00Z",
            "date_to": "2017-12-28T10:00:00Z",
            "date_admission": None,
            "is_public": False,
            "presale_start": None,
            "presale_end": None,
            "location": None,
            "slug": "2030",
            "meta_data": {
                "type": "Conference"
            }
        },
        format='json'
    )

    assert resp.status_code == 201

    resp = token_client.post(
        '/api/v1/organizers/{}/events/'.format(organizer.slug),
        {
            "name": {
                "de": "Demo Konference 2020 Test",
                "en": "Demo Conference 2020 Test"
            },
            "live": False,
            "currency": "EUR",
            "date_from": "2017-12-27T10:00:00Z",
            "date_to": "2017-12-28T10:00:00Z",
            "date_admission": None,
            "is_public": False,
            "presale_start": None,
            "presale_end": None,
            "location": None,
            "slug": event.slug,
            "meta_data": {
                "type": "Conference"
            }
        },
        format='json'
    )
    assert resp.status_code == 400
    assert resp.content.decode() == '{"slug":["This slug has already been used for a different event."]}'

    resp = token_client.post(
        '/api/v1/organizers/{}/events/'.format(organizer.slug),
        {
            "name": {
                "de": "Demo Konference 2020 Test",
                "en": "Demo Conference 2020 Test"
            },
            "live": True,
            "currency": "EUR",
            "date_from": "2017-12-27T10:00:00Z",
            "date_to": "2017-12-28T10:00:00Z",
            "date_admission": None,
            "is_public": False,
            "presale_start": None,
            "presale_end": None,
            "location": None,
            "slug": "2031",
            "meta_data": {
                "type": "Conference"
            }
        },
        format='json'
    )
    assert resp.status_code == 400
    assert resp.content.decode() == '{"live":["Events cannot be create as \'live\'. Quotas and payment must be added ' \
                                    'to the event before sales can go live."]}'


@pytest.mark.django_db
def test_event_create_with_clone(token_client, organizer, event):
    resp = token_client.post(
        '/api/v1/organizers/{}/events/{}/clone/'.format(organizer.slug, event.slug),
        {
            "name": {
                "de": "Demo Konference 2020 Test",
                "en": "Demo Conference 2020 Test"
            },
            "live": False,
            "currency": "EUR",
            "date_from": "2018-12-27T10:00:00Z",
            "date_to": "2018-12-28T10:00:00Z",
            "date_admission": None,
            "is_public": False,
            "presale_start": None,
            "presale_end": None,
            "location": None,
            "slug": "2030",
            "meta_data": {
                "type": "Conference"
            },
            "plugins": {
                "pretix.plugins.ticketoutputpdf"
            }
        },
        format='json'
    )

    assert resp.status_code == 201
    event = Event.objects.get(organizer=organizer.pk, slug='2030')
    assert event.plugins == 'pretix.plugins.ticketoutputpdf'


@pytest.mark.django_db
def test_event_update(token_client, organizer, event, item):
    resp = token_client.patch(
        '/api/v1/organizers/{}/events/{}/'.format(organizer.slug, event.slug),
        {
            "date_from": "2018-12-27T10:00:00Z",
            "date_to": "2018-12-28T10:00:00Z",
            "currency": "DKK",
        },
        format='json'
    )
    assert resp.status_code == 200
    event = Event.objects.get(organizer=organizer.pk, slug=resp.data['slug'])
    assert event.currency == "DKK"

    resp = token_client.patch(
        '/api/v1/organizers/{}/events/{}/'.format(organizer.slug, event.slug),
        {
            "date_from": "2017-12-27T10:00:00Z",
            "date_to": "2017-12-26T10:00:00Z"
        },
        format='json'
    )
    assert resp.status_code == 400
    assert resp.content.decode() == '{"non_field_errors":["The event cannot end before it starts."]}'

    resp = token_client.patch(
        '/api/v1/organizers/{}/events/{}/'.format(organizer.slug, event.slug),
        {
            "presale_start": "2017-12-27T10:00:00Z",
            "presale_end": "2017-12-26T10:00:00Z"
        },
        format='json'
    )
    assert resp.status_code == 400
    assert resp.content.decode() == '{"non_field_errors":["The event\'s presale cannot end before it starts."]}'

    resp = token_client.patch(
        '/api/v1/organizers/{}/events/{}/'.format(organizer.slug, event.slug),
        {
            "slug": "testing"
        },
        format='json'
    )
    assert resp.status_code == 400
    assert resp.content.decode() == '{"slug":["The event slug cannot be changed."]}'


@pytest.mark.django_db
def test_event_update_live_no_product(token_client, organizer, event):
    resp = token_client.patch(
        '/api/v1/organizers/{}/events/{}/'.format(organizer.slug, event.slug),
        {
            "live": True
        },
        format='json'
    )
    assert resp.status_code == 400
    assert resp.content.decode() == '{"live":["You need to configure at least one quota to sell anything."]}'


@pytest.mark.django_db
def test_event_update_live_no_payment_method(token_client, organizer, event, item):
    resp = token_client.patch(
        '/api/v1/organizers/{}/events/{}/'.format(organizer.slug, event.slug),
        {
            "live": True
        },
        format='json'
    )
    assert resp.status_code == 400
    assert resp.content.decode() == '{"live":["You have configured at least one paid product but have not enabled any ' \
                                    'payment methods."]}'


@pytest.mark.django_db
def test_event_update_live_free_product(token_client, organizer, event, free_item, free_quota):
    resp = token_client.patch(
        '/api/v1/organizers/{}/events/{}/'.format(organizer.slug, event.slug),
        {
            "live": True
        },
        format='json'
    )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_event_update_plugins(token_client, organizer, event, free_item, free_quota):
    resp = token_client.patch(
        '/api/v1/organizers/{}/events/{}/'.format(organizer.slug, event.slug),
        {
            "plugins": [
                "pretix.plugins.ticketoutputpdf",
                "pretix.plugins.pretixdroid"
            ]
        },
        format='json'
    )
    assert resp.status_code == 200
    assert resp.data.get('plugins') == {
        "pretix.plugins.ticketoutputpdf",
        "pretix.plugins.pretixdroid"
    }

    resp = token_client.patch(
        '/api/v1/organizers/{}/events/{}/'.format(organizer.slug, event.slug),
        {
            "plugins": {
                "pretix.plugins.banktransfer"
            }
        },
        format='json'
    )
    assert resp.status_code == 200
    assert resp.data.get('plugins') == {
        "pretix.plugins.banktransfer"
    }

    resp = token_client.patch(
        '/api/v1/organizers/{}/events/{}/'.format(organizer.slug, event.slug),
        {
            "plugins": {
                "pretix.plugins.test"
            }
        },
        format='json'
    )
    assert resp.status_code == 400
    assert resp.content.decode() == '{"plugins":["Unknown plugin: \'pretix.plugins.test\'."]}'


@pytest.mark.django_db
def test_event_detail(token_client, organizer, event, team):
    team.all_events = True
    team.save()
    resp = token_client.get('/api/v1/organizers/{}/events/{}/'.format(organizer.slug, event.slug))
    assert resp.status_code == 200
    assert TEST_EVENT_RES == resp.data


@pytest.mark.django_db
def test_event_delete(token_client, organizer, event):
    resp = token_client.delete('/api/v1/organizers/{}/events/{}/'.format(organizer.slug, event.slug))
    assert resp.status_code == 204
    assert not organizer.events.filter(pk=event.id).exists()


@pytest.mark.django_db
def test_event_with_order_position_not_delete(token_client, organizer, event, item, order_position):
    resp = token_client.delete('/api/v1/organizers/{}/events/{}/'.format(organizer.slug, event.slug))
    assert resp.status_code == 403
    assert organizer.events.filter(pk=event.id).exists()


@pytest.mark.django_db
def test_event_with_cart_position_not_delete(token_client, organizer, event, item, cart_position):
    resp = token_client.delete('/api/v1/organizers/{}/events/{}/'.format(organizer.slug, event.slug))
    assert resp.status_code == 403
    assert organizer.events.filter(pk=event.id).exists()
